"""Linha de comando: `breeze` ou `python -m breeze`."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .curva import ConfigInvalida, Configuracao, carregar
from .daemon import Daemon, ErroFatal
from .sysfs import Applesmc

CONFIG_PADRAO = "/etc/breeze.json"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="breeze",
        description="Breeze: controle de ventoinha para MacBook com Linux (applesmc).")
    p.add_argument("--config", default=CONFIG_PADRAO,
                   help="arquivo JSON da curva (padrao: %(default)s; se nao existir, usa a curva padrao)")
    p.add_argument("--raiz", default="/",
                   help="raiz do sistema de arquivos (aponte para uma arvore falsa para testar)")
    p.add_argument("--simular", action="store_true",
                   help="le os sensores e imprime a decisao, sem escrever nada")
    p.add_argument("--ciclos", type=int, default=None,
                   help="para depois de N ciclos (padrao: roda ate receber SIGTERM)")
    p.add_argument("--validar", metavar="ARQ", help="valida um arquivo de configuracao e sai")
    p.add_argument("--padrao", action="store_true", help="imprime a configuracao padrao e sai")
    p.add_argument("--versao", action="version", version=f"%(prog)s {__version__}")
    return p


def _config(caminho: str) -> Configuracao:
    if Path(caminho).exists():
        return carregar(caminho)
    print(f"{caminho} nao existe: usando a curva padrao", file=sys.stderr)
    return Configuracao()


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.padrao:
        print(json.dumps(Configuracao().como_dict(), indent=2))
        return 0

    if args.validar:
        try:
            cfg = carregar(args.validar)
        except ConfigInvalida as e:
            print(f"invalido: {e}")
            return 1
        print(f"ok: {len(cfg.curva)} pontos, piso {cfg.piso_rpm} rpm, "
              f"emergencia a {cfg.emergencia_c:g} °C")
        return 0

    try:
        cfg = _config(args.config)
    except ConfigInvalida as e:
        print(f"configuracao invalida: {e}", file=sys.stderr)
        return 2

    smc = Applesmc(args.raiz, somente_leitura=args.simular)
    if not smc.dir.is_dir():
        print(f"nao achei {smc.dir} (driver applesmc carregado?)", file=sys.stderr)
        return 3

    try:
        Daemon(smc, cfg, simular=args.simular).executar(ciclos=args.ciclos)
    except ErroFatal as e:
        print(f"erro fatal: {e}", file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
