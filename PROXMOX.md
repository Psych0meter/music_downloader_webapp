# Proxmox LXC Install Scripts

These scripts follow the [community-scripts/ProxmoxVE](https://github.com/community-scripts/ProxmoxVE) convention to deploy **Music Downloader** as a bare-Python service inside a Debian 12 LXC container on Proxmox.

## File Structure

```
music_downloader_webapp/
├── ct/
│   └── music-downloader.sh         # Run on Proxmox host — creates the LXC
├── install/
│   └── music-downloader-install.sh # Run inside the container — installs the app
└── Dockerfile                      # (fixed) Docker alternative
```

## Usage

Run the following **on your Proxmox host shell**:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Psych0meter/music_downloader_webapp/main/ct/music-downloader.sh)"
```

The interactive wizard will ask about container resources (or use defaults below).

### Default Settings

| Setting      | Value          |
|-------------|----------------|
| OS          | Debian 13      |
| CPU         | 1 core         |
| RAM         | 512 MB         |
| Disk        | 4 GB           |
| Port        | 5000           |
| Unprivileged| Yes            |
| Downloads   | `/opt/music-downloader/downloads` |

## What the Scripts Do

1. **`ct/music-downloader.sh`** (runs on Proxmox host):
   - Prompts for container settings (default or advanced)
   - Downloads a Debian 12 template if needed
   - Creates and configures the LXC container
   - Runs the install script inside the container via `pct exec`

2. **`install/music-downloader-install.sh`** (runs inside the container):
   - Updates the OS
   - Installs Python 3, git, pip
   - Clones this repository to `/opt/music-downloader`
   - Creates a Python venv and installs `requirements.txt`
   - Creates and enables a `systemd` service (`music-downloader`)
   - Sets up the downloads directory at `/opt/music-downloader/downloads`

## Accessing the App

Once installed, access the web UI at:

```
http://<LXC-IP>:5000
```

The LXC IP is shown at the end of the install script output.

## Updating

Re-run the container script and select **Update** when prompted, or SSH into the container and run:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Psych0meter/music_downloader_webapp/main/ct/music-downloader.sh)"
```

Or manually inside the container:

```bash
cd /opt/music-downloader
git pull
systemctl restart music-downloader
```

## Persistent Music Storage (Optional)

To store downloads on a Proxmox host path instead of inside the container, add a bind mount **on the Proxmox host** after container creation:

```bash
# Replace 100 with your actual CTID, and adjust the host path
pct set 100 -mp0 /mnt/your/music,mp=/opt/music-downloader/downloads
```

Then restart the container:

```bash
pct restart 100
```

## Troubleshooting

Check service status inside the container:

```bash
systemctl status music-downloader
journalctl -u music-downloader -n 50
```
