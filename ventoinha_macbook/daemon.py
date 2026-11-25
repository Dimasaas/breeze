"""Laco principal: le o sensor, decide, escreve, e devolve o controle ao sair."""
from __future__ import annotations

import signal
import sys
import threading
import time
from typing import Callable

from .controle import Controlador, Decisao
from .curva import Configuracao
from .sysfs import Applesmc, ErroSysfs

# Quantos ciclos seguidos com erro de escrita antes de desistir (o systemd religa).
MAX_ERROS_SEGUIDOS = 5
# Reenvia o rpm de tempos em tempos mesmo sem mudanca (o SMC pode "esquecer").
REENVIO_S = 10.0


class ErroFatal(RuntimeError):
    """Erros demais seguidos: o daemon desiste para o supervisor religar."""


def _saida_padrao(msg: str) -> None:
    print(time.strftime("%Y-%m-%d %H:%M:%S"), msg, file=sys.stdout, flush=True)


class Daemon:
    def __init__(self, smc: Applesmc, cfg: Configuracao, simular: bool = False,
                 saida: Callable[[str], None] = _saida_padrao,
                 relogio: Callable[[], float] = time.monotonic):
        self.smc = smc
        self.cfg = cfg
        self.simular = simular
        self.saida = saida
        self.relogio = relogio
        self.controle = Controlador(cfg, smc.rpm_max())
        self._parar = threading.Event()
        self._erros = 0
        self._enviado: int | None = None
        self._ult_envio = 0.0
        self._ult_motivo: str | None = None

    # ------------------------------------------------------------ ciclo
    def ciclo(self) -> Decisao:
        """Uma leitura, uma decisao e (fora da simulacao) uma escrita."""
        try:
            temp = self.smc.temperatura()
        except Exception:
            temp = None
        d = self.controle.decidir(temp)

        if self.simular:
            self.saida(d.texto())
            return d

        if d.motivo != self._ult_motivo and d.motivo in ("emergencia", "sensor"):
            self.saida(f"ATENCAO: {d.texto()}")
        self._ult_motivo = d.motivo

        try:
            # alguem tirou do manual (outro programa)? retoma
            if self.smc.modo_manual() is False:
                self.saida("fan1_manual voltou a 0; retomando o controle")
                self.smc.definir_manual(True)
                self._enviado = None
            agora = self.relogio()
            if d.rpm != self._enviado or agora - self._ult_envio >= REENVIO_S:
                self.smc.pedir_rpm(d.rpm)
                if d.rpm != self._enviado:
                    self.saida(d.texto())
                self._enviado, self._ult_envio = d.rpm, agora
            self._erros = 0
        except ErroSysfs as e:
            self._erros += 1
            self.saida(f"erro de escrita ({self._erros} seguido): {e}")
            if self._erros >= MAX_ERROS_SEGUIDOS:
                raise ErroFatal(str(e)) from e
        return d

    # ------------------------------------------------------------ ciclo de vida
    def parar(self, *_args) -> None:
        """Pede para o laco terminar (usado pelo SIGTERM/SIGINT)."""
        self._parar.set()

    def _instalar_sinais(self) -> None:
        for nome in ("SIGTERM", "SIGINT"):
            sig = getattr(signal, nome, None)
            if sig is None:
                continue
            try:
                signal.signal(sig, self.parar)
            except ValueError:   # fora da thread principal
                pass

    def executar(self, ciclos: int | None = None,
                 dormir: Callable[[float], object] | None = None) -> None:
        dormir = dormir or self._parar.wait
        if not self.simular:
            self._instalar_sinais()
            self.smc.definir_manual(True)
            self.saida("controle manual ligado (piso %d rpm, emergencia a %g °C)"
                       % (self.cfg.piso_rpm, self.cfg.emergencia_c))
        n = 0
        try:
            while not self._parar.is_set() and (ciclos is None or n < ciclos):
                self.ciclo()
                n += 1
                dormir(self.cfg.intervalo_s)
        finally:
            self._devolver_ao_automatico()

    def _devolver_ao_automatico(self) -> None:
        if self.simular:
            return
        try:
            self.smc.definir_manual(False)
            self.saida("fim: fan1_manual = 0 (o SMC voltou a controlar a ventoinha)")
        except ErroSysfs as e:
            self.saida(f"fim: nao consegui devolver o controle ao SMC ({e})")
