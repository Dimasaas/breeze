#!/bin/bash
# Instala o ventoinha-macbook como servico systemd.
# Uso: sudo ./instalar.sh
# Se o servico nao subir, desfaz tudo e devolve a ventoinha ao automatico.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || exec sudo -n bash "$0" "$@"

ORIGEM="$(cd "$(dirname "$0")" && pwd)"
DESTINO=/opt/ventoinha-macbook
CONFIG=/etc/ventoinha-macbook.json
UNIT=/etc/systemd/system/ventoinha-macbook.service
SMC=/sys/devices/platform/applesmc.768

[ -e "$SMC/fan1_output" ] || { echo "ERRO: $SMC/fan1_output nao existe (driver applesmc carregado?)"; exit 1; }
command -v python3 >/dev/null || { echo "ERRO: python3 nao encontrado"; exit 1; }
python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || { echo "ERRO: precisa de Python 3.10+"; exit 1; }

install -d -m 755 "$DESTINO"
rm -rf "$DESTINO/ventoinha_macbook"
cp -r "$ORIGEM/ventoinha_macbook" "$DESTINO/"
find "$DESTINO" -name __pycache__ -prune -exec rm -rf {} +
chmod -R go-w "$DESTINO"

# configuracao: mantem a existente se for valida; senao, copia a de exemplo
if [ -f "$CONFIG" ] && ! PYTHONPATH="$DESTINO" python3 -m ventoinha_macbook --validar "$CONFIG" >/dev/null; then
  mv "$CONFIG" "$CONFIG.invalida.$(date +%s)"
fi
[ -f "$CONFIG" ] || install -m 644 "$ORIGEM/systemd/ventoinha-macbook.json" "$CONFIG"
PYTHONPATH="$DESTINO" python3 -m ventoinha_macbook --validar "$CONFIG"

install -m 644 "$ORIGEM/systemd/ventoinha-macbook.service" "$UNIT"
systemctl daemon-reload
systemctl disable --now mbpfan.service 2>/dev/null || true
systemctl enable --now ventoinha-macbook.service

sleep 4
if ! systemctl is-active --quiet ventoinha-macbook.service; then
  echo "ERRO: o servico nao subiu; desfazendo"
  journalctl -u ventoinha-macbook -n 20 --no-pager || true
  systemctl disable --now ventoinha-macbook.service || true
  echo 0 > "$SMC/fan1_manual" 2>/dev/null || true
  exit 1
fi
echo "ventoinha-macbook ativo. Acompanhe com: journalctl -fu ventoinha-macbook"
