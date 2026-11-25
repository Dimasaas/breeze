#!/bin/bash
# Instala o breeze como servico systemd.
# Uso: sudo ./instalar.sh
# Se o servico nao subir, desfaz tudo e devolve a ventoinha ao automatico.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || exec sudo -n bash "$0" "$@"

ORIGEM="$(cd "$(dirname "$0")" && pwd)"
DESTINO=/opt/breeze
CONFIG=/etc/breeze.json
UNIT=/etc/systemd/system/breeze.service
SMC=/sys/devices/platform/applesmc.768

[ -e "$SMC/fan1_output" ] || { echo "ERRO: $SMC/fan1_output nao existe (driver applesmc carregado?)"; exit 1; }
command -v python3 >/dev/null || { echo "ERRO: python3 nao encontrado"; exit 1; }
python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || { echo "ERRO: precisa de Python 3.10+"; exit 1; }

install -d -m 755 "$DESTINO"
rm -rf "$DESTINO/breeze"
cp -r "$ORIGEM/breeze" "$DESTINO/"
find "$DESTINO" -name __pycache__ -prune -exec rm -rf {} +
chmod -R go-w "$DESTINO"

# configuracao: mantem a existente se for valida; senao, copia a de exemplo
if [ -f "$CONFIG" ] && ! PYTHONPATH="$DESTINO" python3 -m breeze --validar "$CONFIG" >/dev/null; then
  mv "$CONFIG" "$CONFIG.invalida.$(date +%s)"
fi
[ -f "$CONFIG" ] || install -m 644 "$ORIGEM/systemd/breeze.json" "$CONFIG"
PYTHONPATH="$DESTINO" python3 -m breeze --validar "$CONFIG"

install -m 644 "$ORIGEM/systemd/breeze.service" "$UNIT"
systemctl daemon-reload
systemctl disable --now mbpfan.service 2>/dev/null || true
systemctl enable --now breeze.service

sleep 4
if ! systemctl is-active --quiet breeze.service; then
  echo "ERRO: o servico nao subiu; desfazendo"
  journalctl -u breeze -n 20 --no-pager || true
  systemctl disable --now breeze.service || true
  echo 0 > "$SMC/fan1_manual" 2>/dev/null || true
  exit 1
fi
echo "breeze ativo. Acompanhe com: journalctl -fu breeze"
