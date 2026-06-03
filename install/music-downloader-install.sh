#!/usr/bin/env bash
# Copyright (c) 2024 Psych0meter
# Author: Psych0meter
# License: MIT | https://github.com/Psych0meter/music_downloader_webapp/blob/main/LICENSE
# Source: https://github.com/Psych0meter/music_downloader_webapp

# This script is fetched from GitHub and run inside the LXC container via
# lxc-attach from ct/music-downloader.sh. It does NOT use $FUNCTIONS_FILE_PATH
# because that path only exists on the Proxmox host, not inside the container.
# We provide our own minimal helpers below so the script is fully self-contained.

set -euo pipefail

# ---------------------------------------------------------------------------
# Minimal helpers (mirrors community-scripts style output without the host deps)
# ---------------------------------------------------------------------------
YW=$(echo "\033[33m"); GN=$(echo "\033[1;92m"); RD=$(echo "\033[01;31m"); CL=$(echo "\033[m")
CM="  ✔️  "; CROSS="  ✖️  "; INFO="  💡  "

msg_info()  { echo -e "  ⏳  ${YW}${1}${CL}"; }
msg_ok()    { echo -e "${CM}${GN}${1}${CL}"; }
msg_error() { echo -e "${CROSS}${RD}${1}${CL}"; exit 1; }

# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

msg_info "Updating OS"
apt-get update -qq
apt-get upgrade -y -qq
msg_ok "OS Updated"

msg_info "Installing Dependencies"
apt-get install -y -qq \
  curl \
  git \
  python3 \
  python3-pip \
  python3-venv
msg_ok "Installed Dependencies"

msg_info "Cloning Music Downloader Repository"
RELEASE=$(curl -fsSL "https://api.github.com/repos/Psych0meter/music_downloader_webapp/commits/debug" \
  | grep '"sha"' | head -1 | awk '{print substr($2, 2, 8)}')
git clone -q https://github.com/Psych0meter/music_downloader_webapp.git /opt/music-downloader
echo "${RELEASE}" > /opt/music-downloader_version.txt
msg_ok "Cloned Repository (ref: ${RELEASE})"

msg_info "Setting Up Python Virtual Environment"
python3 -m venv /opt/music-downloader/venv
/opt/music-downloader/venv/bin/pip install --upgrade pip --quiet
/opt/music-downloader/venv/bin/pip install -r /opt/music-downloader/requirements.txt --quiet
msg_ok "Python Environment Ready"

msg_info "Creating Downloads Directory"
mkdir -p /opt/music-downloader/downloads
chmod 775 /opt/music-downloader/downloads
msg_ok "Downloads Directory Created"

msg_info "Creating Systemd Service"
cat <<EOF >/etc/systemd/system/music-downloader.service
[Unit]
Description=Music Downloader Web App
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/music-downloader
ExecStart=/opt/music-downloader/venv/bin/python app.py
Restart=always
RestartSec=5
Environment=DOWNLOAD_DIR=/opt/music-downloader/downloads
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable -q --now music-downloader
msg_ok "Service Created and Started"

sleep 2
if ! systemctl is-active --quiet music-downloader; then
  msg_error "Service failed to start. Run: journalctl -u music-downloader -n 30"
fi

msg_info "Cleaning Up"
apt-get -y autoremove -qq
apt-get -y autoclean -qq
msg_ok "Cleaned Up"

echo -e "\n${CM}${GN}Music Downloader installed successfully!${CL}"
echo -e "${INFO}${YW}Access at: http://$(hostname -I | awk '{print $1}'):5000${CL}\n"
