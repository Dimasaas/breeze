"""Arvore sysfs falsa (e, mais adiante, um modelo termico) para testes e demos."""
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
