"""Acesso ao driver applesmc pelo sysfs.

Toda a conversa com o hardware passa por esta classe. O parametro `raiz`
permite apontar para uma arvore falsa (um diretorio temporario) nos testes e
no modo de simulacao, sem tocar em nenhum arquivo real.
"""
from __future__ import annotations

from pathlib import Path

DIRETORIO_APPLESMC = "sys/devices/platform/applesmc.768"

# Leituras fora desta faixa (em °C) sao tratadas como defeito do sensor.
TEMP_MIN_C = 5.0
TEMP_MAX_C = 120.0


class ErroSysfs(RuntimeError):
    """Falha ao ler ou escrever um arquivo do sysfs."""


class Applesmc:
    def __init__(self, raiz: str | Path = "/", somente_leitura: bool = False):
        self.raiz = Path(raiz)
        self.somente_leitura = somente_leitura
        self.dir = self.raiz / DIRETORIO_APPLESMC

    # ------------------------------------------------------------ baixo nivel
    def _ler(self, nome: str) -> str:
        try:
            return (self.dir / nome).read_text(encoding="ascii").strip()
        except (OSError, UnicodeDecodeError) as e:
            raise ErroSysfs(f"nao consegui ler {nome}: {e}") from e

    def _escrever(self, nome: str, valor: int) -> None:
        if self.somente_leitura:
            raise ErroSysfs("escrita bloqueada (modo somente leitura)")
        try:
            (self.dir / nome).write_text(str(int(valor)), encoding="ascii")
        except OSError as e:
            raise ErroSysfs(f"nao consegui escrever {nome}: {e}") from e

    # ------------------------------------------------------------ temperaturas
    def temperaturas(self) -> list[float]:
        """Temperaturas validas, em °C.

        Usa so os sensores de CPU (rotulos que comecam com "TC"); se o
        driver nao rotular nenhum, usa todos. Entradas ilegiveis ou absurdas
        sao descartadas: quem decide o que fazer sem leitura e o controlador.
        """
        cpu: list[float] = []
        todas: list[float] = []
        rotulados = False
        for arq in sorted(self.dir.glob("temp*_input")):
            rotulo = arq.with_name(arq.name.replace("_input", "_label"))
            try:
                eh_cpu = rotulo.read_text(encoding="ascii").strip().upper().startswith("TC")
            except OSError:
                eh_cpu = False
            else:
                rotulados = rotulados or eh_cpu
            try:
                valor = int(arq.read_text(encoding="ascii").strip()) / 1000.0
            except (OSError, ValueError):
                continue
            if not TEMP_MIN_C <= valor <= TEMP_MAX_C:
                continue
            todas.append(valor)
            if eh_cpu:
                cpu.append(valor)
        # sem nenhum rotulo de CPU no driver, usa tudo; com rotulo, so a CPU
        return cpu if rotulados else todas

    def temperatura(self) -> float | None:
        """A maior temperatura de CPU, ou None se nenhum sensor respondeu."""
        valores = self.temperaturas()
        return max(valores) if valores else None

    # ------------------------------------------------------------ ventoinha
    def rpm_max(self, padrao: int = 6200) -> int:
        try:
            valor = int(self._ler("fan1_max"))
        except (ErroSysfs, ValueError):
            return padrao
        return valor if valor > 0 else padrao

    def rpm_min_reportado(self) -> int | None:
        """fan1_min como o driver informa (pode ser mais alto que o piso real)."""
        try:
            return int(self._ler("fan1_min"))
        except (ErroSysfs, ValueError):
            return None

    def rpm_atual(self) -> int | None:
        try:
            return int(self._ler("fan1_input"))
        except (ErroSysfs, ValueError):
            return None

    def modo_manual(self) -> bool | None:
        try:
            return self._ler("fan1_manual") == "1"
        except ErroSysfs:
            return None

    def definir_manual(self, ligado: bool) -> None:
        self._escrever("fan1_manual", 1 if ligado else 0)

    def pedir_rpm(self, rpm: int) -> None:
        self._escrever("fan1_output", rpm)
