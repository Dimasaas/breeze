"""Arvore sysfs falsa e um modelo termico, para testes e demos."""
from __future__ import annotations

from pathlib import Path

from .sysfs import DIRETORIO_APPLESMC

SENSORES_CPU = ("TC0P", "TC0C", "TC1C")


def arvore_falsa(raiz: str | Path, temp_c: float = 40.0, rpm_max: int = 6200,
                 fan_min: int = 4000) -> Path:
    """Cria, sob `raiz`, os arquivos do applesmc que o daemon usa."""
    d = Path(raiz) / DIRETORIO_APPLESMC
    d.mkdir(parents=True, exist_ok=True)
    for i, nome in enumerate(SENSORES_CPU, start=1):
        (d / f"temp{i}_label").write_text(nome + "\n")
        (d / f"temp{i}_input").write_text(str(int(temp_c * 1000)) + "\n")
    # um sensor que nao e de CPU, mais quente, para provar que e ignorado
    (d / "temp9_label").write_text("TB0T\n")
    (d / "temp9_input").write_text("99000\n")
    (d / "fan1_manual").write_text("0\n")
    (d / "fan1_output").write_text("0\n")
    (d / "fan1_input").write_text("0\n")
    (d / "fan1_min").write_text(f"{fan_min}\n")
    (d / "fan1_max").write_text(f"{rpm_max}\n")
    return d


def definir_temperatura(raiz: str | Path, temp_c: float, sensor: int = 1) -> None:
    arq = Path(raiz) / DIRETORIO_APPLESMC / f"temp{sensor}_input"
    arq.write_text(str(int(temp_c * 1000)) + "\n")


class MaquinaTermica:
    """Modelo termico simples: aquecimento por carga, resfriamento por rpm.

    A CPU dissipa `base_w + carga * extra_w` watts. O dissipador tem capacidade
    termica `capacidade` (J/°C) e perde calor para o ambiente com uma
    condutancia que cresce com a rotacao. A cada `passo()` le `fan1_output`
    do sysfs falso e grava as novas temperaturas, fechando o laco com o daemon.
    """

    def __init__(self, raiz: str | Path, carga: float = 0.0, ambiente_c: float = 25.0,
                 base_w: float = 6.0, extra_w: float = 29.0, capacidade: float = 60.0,
                 rpm_max: int = 6200):
        self.dir = Path(raiz) / DIRETORIO_APPLESMC
        self.carga = carga
        self.ambiente_c = ambiente_c
        self.base_w, self.extra_w, self.capacidade = base_w, extra_w, capacidade
        self.rpm_max = rpm_max
        self.rpm = 2000.0
        self.temp = ambiente_c + 15.0
        self.pico = self.temp

    def potencia(self) -> float:
        return self.base_w + self.extra_w * self.carga

    def _pedido(self) -> float:
        try:
            return float((self.dir / "fan1_output").read_text().strip() or 0)
        except (OSError, ValueError):
            return self.rpm

    def passo(self, dt: float = 1.0) -> float:
        pedido = self._pedido()
        if (self.dir / "fan1_manual").read_text().strip() != "1":
            pedido = self.rpm_max * 0.35    # automatico do SMC: rotacao morna
        self.rpm += (pedido - self.rpm) * min(1.0, dt / 2.0)
        condutancia = 0.4 + 0.8 * self.rpm / self.rpm_max
        fluxo = self.potencia() - condutancia * (self.temp - self.ambiente_c)
        self.temp += fluxo / self.capacidade * dt
        self.pico = max(self.pico, self.temp)
        self.escrever()
        return self.temp

    def escrever(self) -> None:
        for i in range(1, len(SENSORES_CPU) + 1):
            (self.dir / f"temp{i}_input").write_text(str(int(self.temp * 1000)) + "\n")
        (self.dir / "fan1_input").write_text(str(int(self.rpm)) + "\n")
