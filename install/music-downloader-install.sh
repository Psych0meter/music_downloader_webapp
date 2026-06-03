#!/usr/bin/env bash
# Copyright (c) 2024 Psych0meter
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

msg_info "Cloning ${APP} Repository"
RELEASE=$(curl -fsSL https://api.github.com/repos/Psych0meter/music_downloader_webapp/commits/main \
  | grep '"sha"' | head -1 | awk '{print substr($2, 2, 8)}')
$STD git clone https://github.com/Psych0meter/music_downloader_webapp.git /opt/music-downloader
msg_ok "Cloned ${APP} Repository (ref: ${RELEASE})"

msg_info "Setting Up Python Environment"
python3 -m venv /opt/music-downloader/venv
/opt/music-downloader/venv/bin/pip install --upgrade pip --quiet
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
msg_ok "Systemd Service Created and Started"

# Verify the service is actually up
sleep 2
if ! systemctl is-active --quiet music-downloader; then
  msg_error "Service failed to start — check: journalctl -u music-downloader -n 30"
  exit 1
fi

# Save version for update detection
echo "${RELEASE}" >/opt/music-downloader_version.txt

motd_ssh
customize

msg_info "Cleaning Up"
$STD apt-get -y autoremove
$STD apt-get -y autoclean
msg_ok "Cleaned Up"

cleanup_lxc
