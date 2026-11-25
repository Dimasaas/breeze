#!/usr/bin/env python3
"""Gera docs/curva.svg a partir da curva padrao (ou de um JSON passado como argumento).

Uso:  python scripts/gerar_curva_svg.py [config.json] [saida.svg]
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from breeze.curva import Configuracao, carregar  # noqa: E402

L, A = 760, 400
ML, MR, MT, MB = 70, 30, 40, 55
T0, T1 = 40.0, 95.0
R0, R1 = 1500, 6500


def x(t: float) -> float:
    return ML + (t - T0) / (T1 - T0) * (L - ML - MR)


def y(r: float) -> float:
    return A - MB - (r - R0) / (R1 - R0) * (A - MT - MB)


PONTOS_TERMICOS = [(0.0, (0x38, 0xBD, 0xF8)), (0.4, (0xFA, 0xCC, 0x15)),
                   (0.7, (0xF9, 0x73, 0x16)), (1.0, (0xDC, 0x26, 0x26))]


def cor_termica(frac: float) -> str:
    """Degrade termico azul -> amarelo -> laranja -> vermelho (so para temperatura)."""
    frac = min(1.0, max(0.0, frac))
    for (f0, c0), (f1, c1) in zip(PONTOS_TERMICOS, PONTOS_TERMICOS[1:]):
        if frac <= f1:
            k = (frac - f0) / (f1 - f0)
            return "#%02X%02X%02X" % tuple(round(a + (b - a) * k) for a, b in zip(c0, c1))
    return "#DC2626"


def gerar(cfg: Configuracao) -> str:
    pontos_sobe = [(t, max(cfg.piso_rpm, cfg.rpm_para(t))) for t in
                   [T0 + i * 0.5 for i in range(int((T1 - T0) * 2) + 1)]]
    sobe = " ".join(f"{x(t):.1f},{y(r):.1f}" for t, r in pontos_sobe)
    # descendo, a curva anda `histerese_c` para a direita (so desce depois de cair a banda)
    desce = " ".join(f"{x(t + cfg.histerese_c):.1f},{y(r):.1f}" for t, r in pontos_sobe
                     if t + cfg.histerese_c <= T1)
    base = A - MB
    area = f"{x(T0):.1f},{base} " + sobe + f" {x(T1):.1f},{base}"
    xa, xb = x(T0), x(T1)
    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {L} {A}" width="{L}" height="{A}" '
             "font-family=\"'Segoe UI', 'Helvetica Neue', system-ui, sans-serif\" font-size=\"13\">")
    o.append("<title>Curva temperatura para rpm</title>")
    o.append("<defs>")
    o.append(f'<linearGradient id="termico" gradientUnits="userSpaceOnUse" x1="{xa:.1f}" y1="0" x2="{xb:.1f}" y2="0">'
             + "".join(f'<stop offset="{f}" stop-color="{c}"/>' for f, c in
                       [(0, "#38BDF8"), (0.4, "#FACC15"), (0.7, "#F97316"), (1, "#DC2626")])
             + "</linearGradient>")
    o.append(f'<linearGradient id="calor" gradientUnits="userSpaceOnUse" x1="0" y1="{MT}" x2="0" y2="{base}">'
             '<stop offset="0" stop-color="#EAF6FF" stop-opacity="0.18"/>'
             '<stop offset="1" stop-color="#EAF6FF" stop-opacity="0"/></linearGradient>')
    o.append("</defs>")
    o.append(f'<rect width="{L}" height="{A}" rx="14" fill="#0C2D48"/>')
    for r in range(2000, 6501, 1000):
        o.append(f'<line x1="{ML}" y1="{y(r):.1f}" x2="{L - MR}" y2="{y(r):.1f}" stroke="#EAF6FF" stroke-opacity="0.1"/>')
        o.append(f'<text x="{ML - 8}" y="{y(r) + 4:.1f}" text-anchor="end" fill="#EAF6FF" fill-opacity="0.8">{r}</text>')
    for t in range(40, 96, 10):
        o.append(f'<line x1="{x(t):.1f}" y1="{MT}" x2="{x(t):.1f}" y2="{base}" stroke="#EAF6FF" stroke-opacity="0.1"/>')
        o.append(f'<text x="{x(t):.1f}" y="{base + 20}" text-anchor="middle" fill="{cor_termica((t - T0) / (T1 - T0))}">{t} °C</text>')
    # faixa de emergencia
    o.append(f'<rect x="{x(cfg.emergencia_c):.1f}" y="{MT}" width="{x(T1) - x(cfg.emergencia_c):.1f}" '
             f'height="{A - MT - MB}" fill="#DC2626" fill-opacity="0.22"/>')
    o.append(f'<line x1="{x(cfg.emergencia_c):.1f}" y1="{MT}" x2="{x(cfg.emergencia_c):.1f}" y2="{base}" '
             f'stroke="#F87171" stroke-dasharray="5 4"/>')
    o.append(f'<text x="{x(cfg.emergencia_c) - 6:.1f}" y="{MT + 14}" text-anchor="end" fill="#F87171">emergência {cfg.emergencia_c:g} °C</text>')
    # piso
    o.append(f'<line x1="{ML}" y1="{y(cfg.piso_rpm):.1f}" x2="{L - MR}" y2="{y(cfg.piso_rpm):.1f}" '
             f'stroke="#38BDF8" stroke-opacity="0.8" stroke-dasharray="2 4"/>')
    o.append(f'<text x="{L - MR - 4}" y="{y(cfg.piso_rpm) + 18:.1f}" text-anchor="end" fill="#38BDF8">piso {cfg.piso_rpm} rpm</text>')
    # curvas
    o.append(f'<polygon points="{area}" fill="url(#calor)"/>')
    o.append(f'<polyline points="{desce}" fill="none" stroke="#38BDF8" stroke-width="2" stroke-dasharray="6 4"/>')
    o.append(f'<polyline points="{sobe}" fill="none" stroke="url(#termico)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
    for t, r in cfg.curva:
        o.append(f'<circle cx="{x(t):.1f}" cy="{y(r):.1f}" r="5" fill="{cor_termica((t - T0) / (T1 - T0))}" stroke="#0C2D48" stroke-width="2"/>')
    # legenda
    o.append(f'<line x1="{ML + 12}" y1="{MT - 18}" x2="{ML + 40}" y2="{MT - 18}" stroke="url(#termico)" stroke-width="4" stroke-linecap="round"/>')
    o.append(f'<text x="{ML + 48}" y="{MT - 14}" fill="#EAF6FF">subindo</text>')
    o.append(f'<line x1="{ML + 130}" y1="{MT - 18}" x2="{ML + 158}" y2="{MT - 18}" stroke="#38BDF8" stroke-width="2" stroke-dasharray="6 4"/>')
    o.append(f'<text x="{ML + 166}" y="{MT - 14}" fill="#EAF6FF">descendo (histerese {cfg.histerese_c:g} °C)</text>')
    o.append(f'<text x="{(ML + L - MR) / 2:.0f}" y="{A - 10}" text-anchor="middle" fill="#EAF6FF" fill-opacity="0.8">temperatura da CPU</text>')
    o.append(f'<text x="16" y="{(MT + A - MB) / 2:.0f}" text-anchor="middle" fill="#EAF6FF" fill-opacity="0.8" '
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
