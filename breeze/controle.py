"""Decisao de rpm: curva + histerese + emergencia + falha de sensor.

Nada aqui toca em hardware: recebe uma temperatura (ou None) e devolve a
decisao. Isso deixa a logica inteira testavel.
"""
from __future__ import annotations

from dataclasses import dataclass

from .curva import Configuracao

# A emergencia so termina quando a temperatura cai esta folga abaixo do limite.
FOLGA_EMERGENCIA_C = 4.0
# Os pedidos de rpm sao arredondados a este passo, para nao gravar 3417, 3421...
PASSO_RPM = 50

MOTIVO_CURVA = "curva"
MOTIVO_HISTERESE = "histerese"
MOTIVO_EMERGENCIA = "emergencia"
MOTIVO_SENSOR = "sensor"


@dataclass(frozen=True)
class Decisao:
    temp: float | None
    rpm: int
    motivo: str
    referencia: float | None = None

    def texto(self) -> str:
        t = "sem leitura" if self.temp is None else f"{self.temp:.1f} °C"
        return f"{t} -> {self.rpm} rpm ({self.motivo})"


class Controlador:
    def __init__(self, cfg: Configuracao, rpm_max: int = 6200):
        self.cfg = cfg
        self.rpm_max = max(rpm_max, cfg.piso_rpm)
        self._ref: float | None = None   # temperatura que "segura" o rpm atual
        self._emergencia = False

    @property
    def em_emergencia(self) -> bool:
        return self._emergencia

    def decidir(self, temp: float | None) -> Decisao:
        # sem leitura confiavel: o mais seguro e girar no maximo
        if temp is None or temp != temp:
            self._ref = None
            return Decisao(None, self.rpm_max, MOTIVO_SENSOR)

        # emergencia com trava: entra no limite, so sai com folga abaixo dele
        if temp >= self.cfg.emergencia_c:
            self._emergencia = True
        elif self._emergencia and temp < self.cfg.emergencia_c - FOLGA_EMERGENCIA_C:
            self._emergencia = False
        if self._emergencia:
            self._ref = temp
            return Decisao(temp, self.rpm_max, MOTIVO_EMERGENCIA, temp)

        # histerese: subindo, acompanha na hora; descendo, so acompanha
        # depois de cair mais que `histerese_c` abaixo da referencia
        h = self.cfg.histerese_c
        motivo = MOTIVO_CURVA
        if self._ref is None or temp > self._ref:
            self._ref = temp
        elif temp < self._ref - h:
            self._ref = temp + h
        elif temp < self._ref:
            motivo = MOTIVO_HISTERESE   # dentro da banda: segura o rpm

        return Decisao(temp, self._rpm(self._ref), motivo, self._ref)

    def _rpm(self, ref: float) -> int:
        bruto = self.cfg.rpm_para(ref)
        passo = int(round(bruto / PASSO_RPM)) * PASSO_RPM
        return max(self.cfg.piso_rpm, min(self.rpm_max, passo))
