#!/usr/bin/env bash
source <(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/misc/build.func)
# Copyright (c) 2026 Psych0meter
# Author: Psych0meter
# License: MIT | https://github.com/Psych0meter/music_downloader_webapp/blob/main/LICENSE
# Source: https://github.com/Psych0meter/music_downloader_webapp

# ---------------------------------------------------------------------------
# Branch to deploy. Defaults to "main".
# To deploy a specific branch, export BRANCH before running:
#   export BRANCH=debug
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/Psych0meter/music_downloader_webapp/main/ct/music-downloader.sh)"
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

  if [[ ! -d /opt/music-downloader ]]; then
    msg_error "No ${APP} Installation Found!"
    exit
  fi

  msg_info "Updating Container OS"
  apt_update_safe
  $STD apt-get -o Dpkg::Options::="--force-confold" -y dist-upgrade
  msg_ok "Updated Container OS"

  msg_info "Stopping Service"
  systemctl stop music-downloader
  msg_ok "Stopped Service"

  # The OS dist-upgrade above can bump the system python3 minor version
  # (e.g. 3.13 -> 3.14) and remove the old versioned binary. The venv's
  # bin/python3 is a symlink pinned to that exact versioned binary, so it
  # goes dangling and every venv/bin/* shim (including pip) breaks. Detect
  # that here and rebuild the venv before we try to use it below, instead
  # of letting pip install fail mid-update.
  msg_info "Checking Python Environment"
  if [[ ! -x /opt/music-downloader/venv/bin/python3 ]] || ! /opt/music-downloader/venv/bin/python3 --version >/dev/null 2>&1; then
    msg_warn "Virtual environment is broken (system Python was likely upgraded) - rebuilding"
    rm -rf /opt/music-downloader/venv
    $STD python3 -m venv /opt/music-downloader/venv
    $STD /opt/music-downloader/venv/bin/pip install --upgrade pip
    msg_ok "Rebuilt Python Virtual Environment"
  else
    msg_ok "Python Environment OK"
  fi

  msg_info "Updating ${APP}"
  cd /opt/music-downloader

  # Read the branch that was originally installed, fall back to main.
  # This handles the case where the container was installed from a branch
  # that no longer exists, or was renamed — bare "git pull" would fail.
  INSTALLED_BRANCH=$(cat /opt/music-downloader_version.txt 2>/dev/null | cut -d'@' -f1)
  INSTALLED_BRANCH="${INSTALLED_BRANCH:-main}"

  $STD git fetch origin
  $STD git checkout "${INSTALLED_BRANCH}"
  $STD git reset --hard "origin/${INSTALLED_BRANCH}"
  $STD /opt/music-downloader/venv/bin/pip install --upgrade -r requirements.txt
  msg_ok "Updated ${APP} (branch: ${INSTALLED_BRANCH})"

  msg_info "Starting Service"
  systemctl start music-downloader
  msg_ok "Started Service"

  msg_ok "Update Successful"
  exit
}

start
build_container

# ---------------------------------------------------------------------------
# Run our install script inside the container.
# build.func's build_container already handles SSH keys and container setup.
# FUNCTIONS_FILE_PATH is passed so the install script can use community-scripts
# helper functions (motd_ssh, customize, cleanup_lxc) for autologin and MOTD.
# Pipe is used instead of bash <() because process substitution requires
# /dev/fd which is unavailable inside lxc-attach.
# ---------------------------------------------------------------------------
msg_info "Running ${APP} Install Script (branch: ${BRANCH})"
curl -fsSL "$INSTALL_SCRIPT_URL" | BRANCH="${BRANCH}" FUNCTIONS_FILE_PATH="${FUNCTIONS_FILE_PATH}" lxc-attach -n "$CTID" -- bash
msg_ok "Install Script Completed"

description

msg_ok "Completed Successfully!\n"
echo -e "${CREATING}${GN}${APP} setup has been successfully initialized!${CL}"
echo -e "${INFO}${YW}Branch deployed: ${BRANCH}${CL}"
echo -e "${INFO}${YW}Access it using the following URL:${CL}"
echo -e "${GATEWAY}${BGN}http://${IP}:5000${CL}"
