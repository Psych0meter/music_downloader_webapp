import os
import re
from urllib.parse import unquote
from bs4 import BeautifulSoup
from curl_cffi import requests
from providers.base import BaseProvider

# curl_cffi handles browser TLS/JA4 signatures and HTTP/2 profiles perfectly to bypass Cloudflare.
_scraper = requests.Session(impersonate="chrome")


class KHInsiderProvider(BaseProvider):
    id = "khinsider"
    name = "KHInsider"
    description = "Video game soundtracks (MP3 / FLAC) from downloads.khinsider.com"

    def _sanitize(self, name, is_album=False):
        name = unquote(name)
        if is_album:
            name = re.sub(
                r'_?MP3_Soundtracks_for_FREE.*$|\s+MP3\s+Soundtracks\s+for\s+FREE.*$',
                '', name, flags=re.IGNORECASE
            )
        return re.sub(r'[\\/*?:"<>|]', "", name).replace(" ", "_")

    def search(self, query):
        res = _scraper.get(
            f"https://downloads.khinsider.com/search?search={query.replace(' ', '+')}",
            timeout=15
        )
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        results = []
        
        for row in soup.select(".albumList tr"):
            # Find all links in the row to avoid hardcoded column indexes
            links = row.find_all("a", href=True)
            album_link = None
            
            # Find the link that belongs to an album and actually has text content
            for a in links:
                if "/game-soundtracks/album/" in a["href"] and a.text.strip():
                    album_link = a
                    break
            
            if album_link:
                url = album_link["href"]
                if not url.startswith("http"):
                    url = f"https://downloads.khinsider.com{url}"
                    
                results.append({
                    "name": album_link.text.strip(),
                    "url": url,
                })
        return results

    def download(self, data):
        preferred_ext = data.get("format", ".flac")
        custom_folder = data.get("folder", "")
        base_path = self.get_path(custom_folder)

        yield {"line": "Analyzing album...", "progress": 0}
        try:
            res = _scraper.get(data.get("url"), timeout=15)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            album_title = self._sanitize(
                soup.find("title").text.replace(" - Download", "").strip(),
                is_album=True
            )
            song_links = sorted(set(
                f"https://downloads.khinsider.com{a['href']}"
                for a in soup.find_all("a", href=True)
                if "/game-soundtracks/album/" in a["href"]
                and a["href"].endswith((".mp3", ".flac", ".m4a"))
            ))

            album_path = os.path.join(base_path, album_title)
            os.makedirs(album_path, exist_ok=True)

            total = len(song_links)
            if total == 0:
                yield {"line": "No tracks found for this album.", "progress": 100}
                return

            for idx, page_url in enumerate(song_links, 1):
                page_soup = BeautifulSoup(
                    _scraper.get(page_url, timeout=15).text, "html.parser"
                )
                audio_links = [
                    a["href"] for a in page_soup.find_all("a", href=True)
                    if a["href"].endswith((".mp3", ".flac", ".m4a"))
                ]
                if not audio_links:
                    continue

                target_url = next(
                    (l for l in audio_links if l.endswith(preferred_ext)),
                    audio_links[0]
                )
                file_name = self._sanitize(os.path.basename(target_url))
                progress = int((idx / total) * 100)

                yield {"line": f"Track {idx}/{total}: {file_name}", "progress": progress}

                # FIX: Removed the context manager 'with' loop which curl_cffi doesn't support
                r = _scraper.get(target_url, stream=True, timeout=30)
                r.raise_for_status()
                with open(os.path.join(album_path, file_name), "wb") as f:
                    for chunk in r.iter_content(65536):
                        f.write(chunk)

            yield {"line": "<span class='text-emerald-400'>=== FINISHED ===</span>", "progress": 100}

        except Exception as e:
            yield {"line": f"<span class='text-red-400'>Error: {str(e)}</span>", "progress": 100}
