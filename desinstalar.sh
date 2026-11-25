#!/bin/bash
# Remove o servico e devolve a ventoinha ao controle automatico do SMC.
# Mantem /etc/breeze.json para uma reinstalacao futura.
# Uso: sudo ./desinstalar.sh
set -uo pipefail
[ "$(id -u)" -eq 0 ] || exec sudo -n bash "$0" "$@"

SMC=/sys/devices/platform/applesmc.768

systemctl disable --now breeze.service 2>/dev/null || true
echo 0 > "$SMC/fan1_manual" 2>/dev/null || true
rm -f /etc/systemd/system/breeze.service
rm -rf /opt/breeze
systemctl daemon-reload
systemctl reset-failed breeze.service 2>/dev/null || true
echo "breeze removido; fan1_manual = 0 (SMC no automatico)."
