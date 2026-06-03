#!/usr/bin/env bash
source <(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/misc/build.func)
# Copyright (c) 2024 Psych0meter
# Author: Psych0meter
# License: MIT | https://github.com/Psych0meter/music_downloader_webapp/blob/main/LICENSE
# Source: https://github.com/Psych0meter/music_downloader_webapp

# ---------------------------------------------------------------------------
# The install script lives in THIS repo, not in community-scripts.
# build.func would try to fetch it from git.community-scripts.org and 404.
# We override by telling build.func to use our own URL via INSTALL_URL,
# and by providing a custom build_container wrapper below.
# ---------------------------------------------------------------------------

APP="Music Downloader"
var_tags="${var_tags:-media;music}"
var_cpu="${var_cpu:-1}"
var_ram="${var_ram:-512}"
var_disk="${var_disk:-4}"
var_os="${var_os:-debian}"
var_version="${var_version:-13}"
var_unprivileged="${var_unprivileged:-1}"

# URL of our own install script (change branch here if needed)
INSTALL_SCRIPT_URL="https://raw.githubusercontent.com/Psych0meter/music_downloader_webapp/debug/install/music-downloader-install.sh"

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
# Run our own install script inside the container.
# build.func's build_container already:
#   - created and started the container
#   - deployed SSH keys (install_ssh_keys_into_ct)
#   - ran customize() for auto-login / motd
# We just need to fetch+run our install script via lxc-attach.
# FUNCTIONS_FILE_PATH is exported by build.func and contains the helper funcs
# the install script needs (msg_info, msg_ok, etc.).
# ---------------------------------------------------------------------------
msg_info "Running ${APP} Install Script"
lxc-attach -n "$CTID" -- bash -c \
  "$(curl -fsSL "$INSTALL_SCRIPT_URL")" \
  -- "$APP" "$FUNCTIONS_FILE_PATH" "$CTID"
msg_ok "Install Script Completed"

description

msg_ok "Completed Successfully!\n"
echo -e "${CREATING}${GN}${APP} setup has been successfully initialized!${CL}"
echo -e "${INFO}${YW} Access it using the following URL:${CL}"
echo -e "${TAB}${GATEWAY}${BGN}http://${IP}:5000${CL}"
