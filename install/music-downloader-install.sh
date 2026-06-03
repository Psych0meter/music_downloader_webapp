#!/usr/bin/env bash
# Copyright (c) 2024 Psych0meter
# Author: Psych0meter
# License: MIT | https://github.com/Psych0meter/music_downloader_webapp/blob/main/LICENSE
# Source: https://github.com/Psych0meter/music_downloader_webapp

set -euo pipefail

# Branch to clone — passed from ct/music-downloader.sh via env var, defaults to "main"
BRANCH="${BRANCH:-main}"

YW=$(echo "\033[33m"); GN=$(echo "\033[1;92m"); RD=$(echo "\033[01;31m"); CL=$(echo "\033[m")
CM="  ✔️  "; CROSS="  ✖️  "

msg_info()  { echo -e "  ⏳  ${YW}${1}${CL}"; }
msg_ok()    { echo -e "${CM}${GN}${1}${CL}"; }
msg_error() { echo -e "${CROSS}${RD}${1}${CL}"; exit 1; }

msg_info "Updating OS"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq
msg_ok "OS Updated"

msg_info "Installing Dependencies"
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  curl \
  git \
  python3 \
  python3-pip \
  python3-venv
msg_ok "Installed Dependencies"

msg_info "Cloning Music Downloader Repository (branch: ${BRANCH})"
RELEASE=$(curl -fsSL "https://api.github.com/repos/Psych0meter/music_downloader_webapp/commits/${BRANCH}" \
  | grep '"sha"' | head -1 | awk '{print substr($2, 2, 8)}')
git clone -q --branch "${BRANCH}" \
  https://github.com/Psych0meter/music_downloader_webapp.git /opt/music-downloader
# Record both the branch and commit for update/debug purposes
echo "${BRANCH}@${RELEASE}" > /opt/music-downloader_version.txt
msg_ok "Cloned Repository (branch: ${BRANCH}, ref: ${RELEASE})"

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

# Enable only — do not start. systemctl start fails inside lxc-attach during
# container creation (systemd not fully initialised). Starts on first boot.
systemctl daemon-reload
systemctl enable -q music-downloader
msg_ok "Service Enabled (will start on first boot)"

msg_info "Cleaning Up"
DEBIAN_FRONTEND=noninteractive apt-get -y autoremove -qq
apt-get -y autoclean -qq
msg_ok "Cleaned Up"

echo -e "\n${CM}${GN}Music Downloader installed successfully!${CL}"
echo -e "  💡  ${YW}Branch: ${BRANCH} (${RELEASE})${CL}"
echo -e "  💡  ${YW}Access at: http://$(hostname -I | awk '{print $1}'):5000 (after container restart)${CL}\n"
