#!/usr/bin/env bash
source <(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/misc/build.func)
# Copyright (c) 2024 Psych0meter
# Author: Psych0meter
# License: MIT | https://github.com/Psych0meter/music_downloader_webapp/blob/main/LICENSE
# Source: https://github.com/Psych0meter/music_downloader_webapp

# ---------------------------------------------------------------------------
# Branch to deploy. Override at runtime with:
#   BRANCH=debug bash -c "$(curl -fsSL ...)"
# Defaults to "main" for normal use.
# ---------------------------------------------------------------------------
BRANCH="${BRANCH:-main}"
REPO="https://github.com/Psych0meter/music_downloader_webapp"
INSTALL_SCRIPT_URL="https://raw.githubusercontent.com/Psych0meter/music_downloader_webapp/${BRANCH}/install/music-downloader-install.sh"

APP="Music Downloader"
var_tags="${var_tags:-media;music}"
var_cpu="${var_cpu:-1}"
var_ram="${var_ram:-512}"
var_disk="${var_disk:-4}"
var_os="${var_os:-debian}"
var_version="${var_version:-13}"
var_unprivileged="${var_unprivileged:-1}"

header_info "$APP"
variables
color
catch_errors

function update_script() {
  header_info
  check_container_storage
  check_container_resources

  if [[ ! -f /opt/music-downloader/app.py ]]; then
    msg_error "No ${APP} Installation Found!"
    exit
  fi

  msg_info "Stopping Service"
  systemctl stop music-downloader
  msg_ok "Stopped Service"

  msg_info "Updating ${APP}"
  cd /opt/music-downloader
  $STD git pull
  $STD /opt/music-downloader/venv/bin/pip install --upgrade -r requirements.txt
  msg_ok "Updated ${APP}"

  msg_info "Starting Service"
  systemctl start music-downloader
  msg_ok "Started Service"

  msg_ok "Update Successful"
  exit
}

start
build_container

# ---------------------------------------------------------------------------
# Run our own install script inside the container, passing BRANCH as an env
# var so the install script clones the correct branch of the app repo.
# ---------------------------------------------------------------------------
msg_info "Running ${APP} Install Script (branch: ${BRANCH})"
# Pipe curl output directly into lxc-attach bash stdin.
# bash <() process substitution does NOT work inside lxc-attach
# because /dev/fd is unavailable in that execution context.
curl -fsSL "$INSTALL_SCRIPT_URL" | BRANCH="${BRANCH}" lxc-attach -n "$CTID" -- bash
msg_ok "Install Script Completed"

description

msg_ok "Completed Successfully!\n"
echo -e "${CREATING}${GN}${APP} setup has been successfully initialized!${CL}"
echo -e "${INFO}${YW} Branch deployed: ${BRANCH}${CL}"
echo -e "${INFO}${YW} Access it using the following URL:${CL}"
echo -e "${TAB}${GATEWAY}${BGN}http://${IP}:5000${CL}"
