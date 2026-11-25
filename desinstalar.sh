#!/bin/bash
# Remove o servico e devolve a ventoinha ao controle automatico do SMC.
# Mantem /etc/ventoinha-macbook.json para uma reinstalacao futura.
# Uso: sudo ./desinstalar.sh
set -uo pipefail
[ "$(id -u)" -eq 0 ] || exec sudo -n bash "$0" "$@"

SMC=/sys/devices/platform/applesmc.768

systemctl disable --now ventoinha-macbook.service 2>/dev/null || true
echo 0 > "$SMC/fan1_manual" 2>/dev/null || true
rm -f /etc/systemd/system/ventoinha-macbook.service
rm -rf /opt/ventoinha-macbook
systemctl daemon-reload
systemctl reset-failed ventoinha-macbook.service 2>/dev/null || true
echo "ventoinha-macbook removido; fan1_manual = 0 (SMC no automatico)."
