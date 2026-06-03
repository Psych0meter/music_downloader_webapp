#!/usr/bin/env bash

# Copyright (c) 2024-2026 Psych0meter
# Author: Psych0meter
# License: MIT | https://github.com/Psych0meter/music_downloader_webapp/blob/main/LICENSE
# Source: https://github.com/Psych0meter/music_downloader_webapp

source /dev/stdin <<<"$FUNCTIONS_FILE_PATH"
color
verb_ip6
catch_errors
setting_up_container
network_check
update_os

msg_info "Installing Dependencies"
$STD apt-get install -y \
  curl \
  git \
  python3 \
  python3-pip \
  python3-venv
msg_ok "Installed Dependencies"

msg_info "Cloning Music Downloader Repository (branch: ${BRANCH})"
$STD git clone -q --branch "${BRANCH}" https://github.com/Psych0meter/music_downloader_webapp.git /opt/music-downloader
RELEASE=$(git -C /opt/music-downloader rev-parse --short HEAD)
echo "${BRANCH}@${RELEASE}" > /opt/music-downloader_version.txt
msg_ok "Cloned Repository (branch: ${BRANCH}, ref: ${RELEASE})"

msg_info "Setting Up Python Virtual Environment"
$STD python3 -m venv /opt/music-downloader/venv
$STD /opt/music-downloader/venv/bin/pip install --upgrade pip
$STD /opt/music-downloader/venv/bin/pip install -r /opt/music-downloader/requirements.txt
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
msg_ok "Created and Enabled Service"

# Crucial lifecycle hooks that fix the Proxmox Web SSH/Console auto-login
motd_ssh
customize
cleanup_lxc
