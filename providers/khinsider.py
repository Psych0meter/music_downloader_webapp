import html
import os
import re
import threading
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup
from curl_cffi import requests

from providers.base import BaseProvider

# Browser fingerprint targets in priority order.
# If the first is blocked by Cloudflare, the session rotates to the next.
_TARGETS = ["chrome146", "chrome145", "chrome136", "firefox147", "chrome124"]

# Only these hosts may be fetched — closes off the "Direct Download" URL box
# (any string starting with "http") from being used as an open SSRF proxy.
_ALLOWED_HOST = "downloads.khinsider.com"

# Sessions are cached per-thread rather than in a single shared global, so
# concurrent requests (two downloads, or a search racing a download) can't
# stomp on each other's fingerprint-rotation state.
_local = threading.local()


def _make_session(target: str) -> requests.Session:
    return requests.Session(impersonate=target)


def _is_allowed_url(url: str) -> bool:
    """Restrict outbound requests to the KHInsider domain (and subdomains)."""
    if not url:
        return False
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    return host == _ALLOWED_HOST or host.endswith(f".{_ALLOWED_HOST}")


def _get(url: str, **kwargs) -> requests.Response:
    """
    GET with automatic fingerprint rotation on 403.
    Tries each target in _TARGETS before giving up. The active session is
    stored in thread-local storage so it can be reused by _local.session
    for the follow-up file download without racing other threads.
    """
    r = None
    for target in _TARGETS:
        session = _make_session(target)
        _local.session = session
        r = session.get(url, **kwargs)
        if r.status_code != 403:
            return r
    # Return last response (caller will raise_for_status)
    return r


class KHInsiderProvider(BaseProvider):
    id = "khinsider"
    name = "KHInsider"
    description = "Video game soundtracks (MP3 / FLAC) from downloads.khinsider.com"
    default_subfolder = "KHInsider"

    def _sanitize(self, name, is_album=False):
        name = unquote(name)
        if is_album:
            name = re.sub(
                r"_?MP3_Soundtracks_for_FREE.*$|\s+MP3\s+Soundtracks\s+for\s+FREE.*$",
                "",
                name,
                flags=re.IGNORECASE,
            )
        return re.sub(r'[\\/*?:"<>|]', "", name).replace(" ", "_")

    def search(self, query):
        res = _get(
            f"https://downloads.khinsider.com/search?search={query.replace(' ', '+')}",
            timeout=15,
        )
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        results = []

        for row in soup.select(".albumList tr"):
            links = row.find_all("a", href=True)
            album_link = None
            for a in links:
                if "/game-soundtracks/album/" in a["href"] and a.text.strip():
                    album_link = a
                    break
            if album_link:
                url = album_link["href"]
                if not url.startswith("http"):
                    url = f"https://downloads.khinsider.com{url}"
                results.append(
                    {
                        "name": album_link.text.strip(),
                        "url": url,
                    }
                )
        return results

    def download(self, data):
        preferred_ext = data.get("format", ".flac")
        custom_folder = data.get("folder", "")
        base_path = self.get_path(custom_folder)
        url = data.get("url", "")

        yield {"line": "Analyzing album...", "progress": 0}

        if not _is_allowed_url(url):
            yield {
                "line": f"<span class='text-red-400'>Error: URL must be on {_ALLOWED_HOST}</span>",
                "progress": 100,
            }
            return

        try:
            res = _get(url, timeout=15)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            album_title = self._sanitize(
                soup.find("title").text.replace(" - Download", "").strip(),
                is_album=True,
            )
            song_links = sorted(
                set(
                    f"https://downloads.khinsider.com{a['href']}"
                    for a in soup.find_all("a", href=True)
                    if "/game-soundtracks/album/" in a["href"] and a["href"].endswith((".mp3", ".flac", ".m4a"))
                )
            )

            album_path = os.path.join(base_path, album_title)
            os.makedirs(album_path, exist_ok=True)

            total = len(song_links)
            if total == 0:
                yield {"line": "No tracks found for this album.", "progress": 100}
                return

            for idx, page_url in enumerate(song_links, 1):
                page_soup = BeautifulSoup(_get(page_url, timeout=15).text, "html.parser")
                audio_links = [
                    a["href"]
                    for a in page_soup.find_all("a", href=True)
                    if a["href"].endswith((".mp3", ".flac", ".m4a"))
                ]
                if not audio_links:
                    continue

                target_url = next(
                    (link for link in audio_links if link.endswith(preferred_ext)),
                    audio_links[0],
                )
                file_name = self._sanitize(os.path.basename(target_url))
                progress = int((idx / total) * 100)

                yield {
                    "line": f"Track {idx}/{total}: {html.escape(file_name)}",
                    "progress": progress,
                }

                r = _local.session.get(target_url, stream=True, timeout=30)
                r.raise_for_status()
                with open(os.path.join(album_path, file_name), "wb") as f:
                    for chunk in r.iter_content(65536):
                        f.write(chunk)

            yield {
                "line": "<span class='text-emerald-400'>=== FINISHED ===</span>",
                "progress": 100,
            }

        except Exception as e:
            yield {
                "line": f"<span class='text-red-400'>Error: {html.escape(str(e))}</span>",
                "progress": 100,
            }
