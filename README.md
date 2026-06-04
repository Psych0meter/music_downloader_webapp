# 🎵 Music Downloader Web App

A self-hosted web application for downloading video game soundtracks and remixes from multiple sources. Built with Flask and a plugin-based provider architecture — adding a new source is as simple as dropping a single Python file.

**Supported providers (out of the box):**
| Provider | Source | What you get |
|----------|--------|--------------|
| KHInsider | [downloads.khinsider.com](https://downloads.khinsider.com) | Video game soundtracks (MP3 / FLAC) |
| OCRemix | [ocremix.org](https://ocremix.org) | Fan-made video game music remixes |

---

## ✨ Features

- 🔍 Search albums / tracks by name
- ⬇️ Live download progress streamed to the browser (Server-Sent Events)
- 🔌 Plugin architecture — add new sources without touching core code
- 📋 In-app log viewer
- 🐳 Docker-ready with health check and multi-platform images (amd64 + arm64)
- 🖥️ Proxmox LXC install script (bare Python, no Docker needed)

---

## 🚀 Quick Start

### Docker (recommended)

```bash
# Clone the repository
git clone https://github.com/Psych0meter/music_downloader_webapp.git
cd music_downloader_webapp

# Start the app (downloads saved to ./downloads by default)
docker compose up -d
```

Then open **http://localhost:5000** in your browser.

> **Tip — change the download path:**
> Edit the `volumes` section in `docker-compose.yml` to point to your music library:
> ```yaml
> volumes:
>   - /your/music/library:/downloads
> ```

### Pre-built image (GHCR)

Images are automatically built and published to the GitHub Container Registry on every tagged release, for both `linux/amd64` and `linux/arm64`.

```bash
docker run -d \
  --name music-downloader \
  -p 5000:5000 \
  -v /your/music/library:/downloads \
  --restart unless-stopped \
  ghcr.io/psych0meter/music_downloader_webapp:latest
```

### Bare Python (local / Proxmox LXC)

```bash
git clone https://github.com/Psych0meter/music_downloader_webapp.git
cd music_downloader_webapp

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

DOWNLOAD_DIR=/your/music python3 app.py
```

Open **http://localhost:5000**.

---

## 🖥️ Proxmox LXC Install (one-liner)

Run the following **on your Proxmox host shell** to create a Debian 13 LXC container and install the app automatically:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Psych0meter/music_downloader_webapp/main/ct/music-downloader.sh)"
```

The interactive wizard will guide you through container settings (or use the defaults below).

| Setting | Default |
|---------|---------|
| OS | Debian 13 |
| CPU | 1 core |
| RAM | 512 MB |
| Disk | 4 GB |
| Port | 5000 |
| Downloads | `/opt/music-downloader/downloads` |

To deploy a specific branch (e.g. for testing):

```bash
export BRANCH=debug
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Psych0meter/music_downloader_webapp/main/ct/music-downloader.sh)"
```

See [`PROXMOX.md`](PROXMOX.md) for full documentation including bind mounts and update instructions.

---

## ⚙️ Configuration

All configuration is done through environment variables (or a `.env` file in the project root):

| Variable | Default | Description |
|----------|---------|-------------|
| `DOWNLOAD_DIR` | `/downloads` | Where downloaded files are saved |
| `PORT` | `5000` | Port the Flask server listens on |
| `FLASK_DEBUG` | `0` | Set to `1` to enable debug mode (development only) |

Copy `.env.example` to `.env` and adjust values as needed — `app.py` loads it automatically on startup.

---

## 🔌 Adding a New Provider

1. Create `providers/my_source.py`
2. Subclass `BaseProvider` and implement `search()` and/or `download()`
3. Restart the app — it will be auto-discovered

```python
# providers/my_source.py
import os
import requests
from typing import Any, Generator
from providers.base import BaseProvider


class MySourceProvider(BaseProvider):
    id = "mysource"
    name = "My Source"
    description = "Downloads from My Source"

    def search(self, query: str) -> list[dict[str, Any]]:
        # Return a list of dicts with at minimum "name" and "url"
        res = requests.get("https://mysource.example/search", params={"q": query})
        return [{"name": r["title"], "url": r["href"]} for r in res.json()]

    def download(self, payload: dict[str, Any]) -> Generator[dict[str, Any], None, None]:
        url = payload["url"]
        dest = os.path.join(os.environ.get("DOWNLOAD_DIR", "/downloads"), "track.mp3")

        yield {"line": f"Downloading {url}", "progress": 10}

        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        yield {"line": "Done!", "progress": 100}
```

Providers that work by ID/range (like OCRemix) can skip `search()` entirely — the base class default returns `[]` and signals `supports_search: false` to the frontend, which then renders a custom form instead.

See [`providers/base.py`](providers/base.py) for the full interface documentation.

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web UI |
| `GET` | `/logs` | Log viewer UI |
| `GET` | `/api/health` | Liveness probe — returns `{"status":"ok","providers":[...]}` |
| `GET` | `/api/info/<provider_id>` | Provider metadata |
| `POST` | `/api/search/<provider_id>` | Search — body: `{"query": "..."}` |
| `POST` | `/api/download/<provider_id>` | Download — body: provider-specific payload, response: SSE stream |

### SSE download stream format

Each event is a JSON object:
```json
{ "line": "Downloading track 3/12...", "progress": 25 }
```
A final event with `"progress": 100` signals completion.

---

## 🗂️ Project Structure

```
music_downloader_webapp/
├── app.py                    # Flask application & provider loader
├── requirements.txt          # Python dependencies
├── Dockerfile                # Container image
├── docker-compose.yml        # Compose stack
├── .env.example              # Environment variable template
│
├── .github/
│   └── workflows/
│       └── docker-build.yml  # CI: builds & pushes multi-platform image to GHCR
│
├── providers/
│   ├── base.py               # BaseProvider abstract class
│   ├── khinsider.py          # KHInsider provider (curl_cffi — Cloudflare bypass)
│   └── ocremix.py            # OCRemix provider (ID/range-based)
│
├── templates/
│   ├── index.html            # Main UI
│   └── logs.html             # Log viewer
│
├── downloads/                # Default download target (gitignored)
│
├── ct/
│   └── music-downloader.sh   # Proxmox host script (creates LXC)
└── install/
    └── music-downloader-install.sh  # In-container install script
```

---

## 🐳 Docker Image & CI/CD

### Automated builds

The GitHub Actions workflow (`.github/workflows/docker-build.yml`) automatically builds and pushes a multi-platform image to GHCR whenever a tag is pushed:

```bash
git tag v1.0.0
git push origin v1.0.0
```

This produces:
- `ghcr.io/psych0meter/music_downloader_webapp:v1.0.0`
- `ghcr.io/psych0meter/music_downloader_webapp:latest`

Both `linux/amd64` and `linux/arm64` platforms are built in a single manifest.

You can also trigger a build manually from the **Actions** tab in GitHub (workflow_dispatch), with an optional branch input.

### Building locally

```bash
docker build -t music-downloader .
docker run -d -p 5000:5000 -v /your/music:/downloads music-downloader
```

---

## 🔄 Updating

### Docker Compose
```bash
docker compose pull
docker compose up -d
```

### Proxmox LXC
Re-run the install script and select **Update**, or SSH into the container:
```bash
cd /opt/music-downloader && git pull
systemctl restart music-downloader
```

---

## 🤝 Contributing

Pull requests are welcome! To add a provider:

1. Fork the repo
2. Create `providers/your_source.py` following the pattern above
3. Test it locally
4. Open a PR

---

## 📄 License

MIT — see [`LICENSE`](LICENSE).
