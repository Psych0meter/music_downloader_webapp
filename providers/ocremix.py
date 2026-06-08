import os, re, time, requests, logging
from bs4 import BeautifulSoup
from providers.base import BaseProvider, HEADERS

logger = logging.getLogger("MediaVault.OCRemix")

# Known mirror domains — any href containing one of these is a valid download link
_MIRROR_DOMAINS = ("ocrmirror.org", "ocr.blueblue.fr", "iterations.org")


class OCRemixProvider(BaseProvider):
    id = "ocremix"
    name = "OCRemix"
    default_subfolder = "OCRemix"

    def get_info(self):
        latest = None
        try:
            res = requests.get("https://ocremix.org/remixes/", headers=HEADERS, timeout=10)
            matches = re.findall(r'/remix/OCR(\d+)', res.text)
            if matches:
                latest = max(int(m) for m in matches)
                logger.info(f"OCRemix: Scraped latest ID {latest}")
        except Exception as e:
            logger.warning(f"OCRemix: Failed to fetch latest online ID: {e}")

        path = self.get_path()
        local_max = None
        if os.path.exists(path):
            files = [f for f in os.listdir(path) if "OCR" in f]
            ids = [int(re.search(r'OCR(\d+)', f).group(1)) for f in files if re.search(r'OCR(\d+)', f)]
            if ids:
                local_max = max(ids)

        info = super().get_info()
        info.update({
            "latest_online": f"OCR{latest:05d}" if latest else "Unknown",
            "last_downloaded": f"OCR{local_max:05d}" if local_max else "Unknown"
        })
        return info

    def _find_download_link(self, soup: BeautifulSoup) -> str | None:
        """
        Find a mirror download link in the page.

        OCRemix uses two formats depending on page version:
          - <a href="https://ocrmirror.org/files/...">...</a>
          - Plain text URLs inside <li> elements (newer pages)
        We check both and accept any known mirror domain.
        """
        # Format 1: standard <a> tags
        for a in soup.find_all("a", href=True):
            if any(domain in a["href"] for domain in _MIRROR_DOMAINS):
                return a["href"]

        # Format 2: bare URLs inside <li> text (newer page structure)
        for li in soup.find_all("li"):
            text = li.get_text(strip=True)
            if text.startswith("http") and any(domain in text for domain in _MIRROR_DOMAINS):
                # Extract just the URL in case there's surrounding text
                match = re.search(r'https?://\S+\.mp3', text)
                if match:
                    return match.group(0)

        return None

    def download(self, data):
        custom_folder = data.get('folder', '')
        dest_path = self.get_path(custom_folder)

        ids = []
        for part in data.get('ids', '').split(','):
            part = part.strip()
            if '-' in part:
                try:
                    s, e = part.split('-')
                    ids.extend(range(int(s), int(e) + 1))
                except:
                    continue
            elif part.isdigit():
                ids.append(int(part))

        if not ids:
            logger.warning("OCRemix: No valid IDs provided for download.")
            yield {"line": "No valid IDs provided.", "progress": 100}
            return

        missing_only = data.get('missing_only', False)
        existing = set(os.listdir(dest_path)) if missing_only and os.path.exists(dest_path) else set()

        for idx, rid_int in enumerate(ids, 1):
            percent = int((idx / len(ids)) * 100)
            rid = f"OCR{rid_int:05d}"

            if missing_only and any(f.startswith(rid) for f in existing):
                yield {"line": f"[{rid}] Skipping (exists)", "progress": percent}
                continue

            try:
                logger.info(f"OCRemix: Processing {rid}...")
                page = requests.get(f"https://ocremix.org/remix/{rid}", headers=HEADERS, timeout=10)
                if page.status_code != 200:
                    logger.error(f"OCRemix: ID {rid} returned HTTP {page.status_code}")
                    yield {"line": f"[{rid}] Request failed (HTTP {page.status_code})", "progress": percent}
                    continue

                soup = BeautifulSoup(page.text, "html.parser")
                link = self._find_download_link(soup)
                if link:
                    fname = os.path.basename(link.split("?")[0])  # strip query string if any
                    yield {"line": f"[{rid}] Downloading: {fname}", "progress": percent}
                    r = requests.get(link, headers=HEADERS, stream=True, timeout=30)
                    r.raise_for_status()
                    with open(os.path.join(dest_path, f"{rid} - {fname}"), "wb") as f:
                        for chunk in r.iter_content(8192):
                            f.write(chunk)
                    logger.info(f"OCRemix: Successfully saved {rid}")
                else:
                    logger.warning(f"OCRemix: No mirror links found for {rid}")
                    yield {"line": f"[{rid}] No mirror link found on page.", "progress": percent}
            except Exception as e:
                logger.error(f"OCRemix: Error during {rid} processing: {str(e)}")
                yield {"line": f"[{rid}] Failed: {str(e)}", "progress": percent}
            time.sleep(0.5)
        yield {"line": "<b>--- Done ---</b>", "progress": 100}
