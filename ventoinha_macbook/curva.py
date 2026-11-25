"""Configuracao e curva temperatura -> rpm."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

PISO_RPM = 2000
EMERGENCIA_C = 88.0
HISTERESE_C = 3.0
INTERVALO_S = 2.0

CURVA_PADRAO = (
    (50.0, 2000),
    (58.0, 2600),
    (66.0, 3400),
    (74.0, 4600),
    (82.0, 5800),
    (88.0, 6200),
)


class ConfigInvalida(ValueError):
    """O arquivo de configuracao nao passou na validacao."""


@dataclass(frozen=True)
class Configuracao:
    curva: tuple[tuple[float, int], ...] = CURVA_PADRAO
    piso_rpm: int = PISO_RPM
    emergencia_c: float = EMERGENCIA_C
    histerese_c: float = HISTERESE_C
    intervalo_s: float = INTERVALO_S

    def __post_init__(self) -> None:
        self.validar()

    def validar(self) -> None:
        if not 2 <= len(self.curva) <= 16:
            raise ConfigInvalida("a curva precisa de 2 a 16 pontos")
        for t, r in self.curva:
            if not 20 <= t <= 100:
                raise ConfigInvalida(f"temperatura {t} fora de 20-100 °C")
            if not 500 <= r <= 10000:
                raise ConfigInvalida(f"rotacao {r} fora de 500-10000 rpm")
        for (t0, r0), (t1, r1) in zip(self.curva, self.curva[1:]):
            if t1 <= t0:
                raise ConfigInvalida("as temperaturas da curva precisam crescer")
            if r1 < r0:
                raise ConfigInvalida("a rotacao nao pode cair quando a temperatura sobe")
        if not 500 <= self.piso_rpm <= 6000:
            raise ConfigInvalida("piso_rpm fora de 500-6000")
        if not 60 <= self.emergencia_c <= EMERGENCIA_C:
            raise ConfigInvalida(f"emergencia_c fora de 60-{EMERGENCIA_C:g} °C")
        if self.curva[-1][0] > self.emergencia_c:
            raise ConfigInvalida("a curva nao pode passar da temperatura de emergencia")
        if not 0 <= self.histerese_c <= 10:
            raise ConfigInvalida("histerese_c fora de 0-10 °C")
        if not 0.5 <= self.intervalo_s <= 30:
            raise ConfigInvalida("intervalo_s fora de 0,5-30 s")

    def rpm_para(self, temp: float) -> float:
        """Interpolacao linear; fora da faixa, fica no primeiro/ultimo ponto."""
        pts = self.curva
        if temp <= pts[0][0]:
            return float(pts[0][1])
        for (t0, r0), (t1, r1) in zip(pts, pts[1:]):
            if temp <= t1:
                return r0 + (r1 - r0) * (temp - t0) / (t1 - t0)
        return float(pts[-1][1])

    def como_dict(self) -> dict:
        return {
            "piso_rpm": self.piso_rpm,
            "emergencia_c": self.emergencia_c,
            "histerese_c": self.histerese_c,
            "intervalo_s": self.intervalo_s,
            "curva": [[t, r] for t, r in self.curva],
        }

    @classmethod
    def de_dict(cls, dados: dict) -> "Configuracao":
        if not isinstance(dados, dict):
            raise ConfigInvalida("a configuracao precisa ser um objeto JSON")
        base = cls()
        try:
            curva = tuple((float(t), int(r)) for t, r in dados.get("curva", base.curva))
            return cls(
                curva=curva,
                piso_rpm=int(dados.get("piso_rpm", base.piso_rpm)),
                emergencia_c=float(dados.get("emergencia_c", base.emergencia_c)),
                histerese_c=float(dados.get("histerese_c", base.histerese_c)),
                intervalo_s=float(dados.get("intervalo_s", base.intervalo_s)),
            )
        except (TypeError, ValueError) as e:
            raise ConfigInvalida(f"valor invalido: {e}") from e


def carregar(caminho: str | Path) -> Configuracao:
    try:
        with open(caminho, encoding="utf-8") as f:
            return Configuracao.de_dict(json.load(f))
    except OSError as e:
        raise ConfigInvalida(f"nao consegui abrir {caminho}: {e}") from e
    except json.JSONDecodeError as e:
        raise ConfigInvalida(f"JSON invalido em {caminho}: {e}") from e
