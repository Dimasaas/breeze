#!/usr/bin/env python3
"""Gera docs/curva.svg a partir da curva padrao (ou de um JSON passado como argumento).

Uso:  python scripts/gerar_curva_svg.py [config.json] [saida.svg]
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from ventoinha_macbook.curva import Configuracao, carregar  # noqa: E402

L, A = 760, 400
ML, MR, MT, MB = 70, 30, 40, 55
T0, T1 = 40.0, 95.0
R0, R1 = 1500, 6500


def x(t: float) -> float:
    return ML + (t - T0) / (T1 - T0) * (L - ML - MR)


def y(r: float) -> float:
    return A - MB - (r - R0) / (R1 - R0) * (A - MT - MB)


def gerar(cfg: Configuracao) -> str:
    pontos_sobe = [(t, max(cfg.piso_rpm, cfg.rpm_para(t))) for t in
                   [T0 + i * 0.5 for i in range(int((T1 - T0) * 2) + 1)]]
    sobe = " ".join(f"{x(t):.1f},{y(r):.1f}" for t, r in pontos_sobe)
    # descendo, a curva anda `histerese_c` para a direita (so desce depois de cair a banda)
    desce = " ".join(f"{x(t + cfg.histerese_c):.1f},{y(r):.1f}" for t, r in pontos_sobe
                     if t + cfg.histerese_c <= T1)
    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {L} {A}" width="{L}" height="{A}" '
             f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="12">')
    o.append("<title>Curva temperatura para rpm</title>")
    o.append(f'<rect width="{L}" height="{A}" rx="12" fill="#14102b"/>')
    for r in range(2000, 6501, 1000):
        o.append(f'<line x1="{ML}" y1="{y(r):.1f}" x2="{L - MR}" y2="{y(r):.1f}" stroke="#ffffff" stroke-opacity="0.08"/>')
        o.append(f'<text x="{ML - 8}" y="{y(r) + 4:.1f}" text-anchor="end" fill="#b9b3d6">{r}</text>')
    for t in range(40, 96, 10):
        o.append(f'<line x1="{x(t):.1f}" y1="{MT}" x2="{x(t):.1f}" y2="{A - MB}" stroke="#ffffff" stroke-opacity="0.08"/>')
        o.append(f'<text x="{x(t):.1f}" y="{A - MB + 20}" text-anchor="middle" fill="#b9b3d6">{t} °C</text>')
    # faixa de emergencia
    o.append(f'<rect x="{x(cfg.emergencia_c):.1f}" y="{MT}" width="{x(T1) - x(cfg.emergencia_c):.1f}" '
             f'height="{A - MT - MB}" fill="#ff5252" fill-opacity="0.14"/>')
    o.append(f'<line x1="{x(cfg.emergencia_c):.1f}" y1="{MT}" x2="{x(cfg.emergencia_c):.1f}" y2="{A - MB}" '
             f'stroke="#ff5252" stroke-dasharray="5 4"/>')
    o.append(f'<text x="{x(cfg.emergencia_c) - 6:.1f}" y="{MT + 14}" text-anchor="end" fill="#ff8a80">emergência {cfg.emergencia_c:g} °C</text>')
    # piso
    o.append(f'<line x1="{ML}" y1="{y(cfg.piso_rpm):.1f}" x2="{L - MR}" y2="{y(cfg.piso_rpm):.1f}" '
             f'stroke="#B388FF" stroke-opacity="0.5" stroke-dasharray="2 4"/>')
    o.append(f'<text x="{L - MR - 4}" y="{y(cfg.piso_rpm) - 6:.1f}" text-anchor="end" fill="#B388FF">piso {cfg.piso_rpm} rpm</text>')
    # curvas
    o.append(f'<polyline points="{desce}" fill="none" stroke="#B388FF" stroke-width="2" stroke-dasharray="6 4"/>')
    o.append(f'<polyline points="{sobe}" fill="none" stroke="#00E5FF" stroke-width="3"/>')
    for t, r in cfg.curva:
        o.append(f'<circle cx="{x(t):.1f}" cy="{y(r):.1f}" r="4" fill="#00E5FF"/>')
    # legenda
    o.append(f'<line x1="{ML + 12}" y1="{MT - 18}" x2="{ML + 40}" y2="{MT - 18}" stroke="#00E5FF" stroke-width="3"/>')
    o.append(f'<text x="{ML + 48}" y="{MT - 14}" fill="#e8e4ff">subindo</text>')
    o.append(f'<line x1="{ML + 130}" y1="{MT - 18}" x2="{ML + 158}" y2="{MT - 18}" stroke="#B388FF" stroke-width="2" stroke-dasharray="6 4"/>')
    o.append(f'<text x="{ML + 166}" y="{MT - 14}" fill="#e8e4ff">descendo (histerese {cfg.histerese_c:g} °C)</text>')
    o.append(f'<text x="{(ML + L - MR) / 2:.0f}" y="{A - 10}" text-anchor="middle" fill="#b9b3d6">temperatura da CPU</text>')
    o.append(f'<text x="16" y="{(MT + A - MB) / 2:.0f}" text-anchor="middle" fill="#b9b3d6" '
             f'transform="rotate(-90 16 {(MT + A - MB) / 2:.0f})">rpm pedido</text>')
    o.append("</svg>")
    return "\n".join(o) + "\n"


def main() -> int:
    cfg = carregar(sys.argv[1]) if len(sys.argv) > 1 else Configuracao()
    saida = Path(sys.argv[2]) if len(sys.argv) > 2 else RAIZ / "docs" / "curva.svg"
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(gerar(cfg), encoding="utf-8")
    print(f"gravado {saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
