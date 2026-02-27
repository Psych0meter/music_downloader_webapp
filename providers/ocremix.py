import os, re, time, requests
from bs4 import BeautifulSoup
from providers.base import BaseProvider, DOWNLOAD_DIR, HEADERS

class OCRemixProvider(BaseProvider):
    id = "ocremix"
    name = "OCRemix"

    def get_info(self):
        latest = 0
        try:
            res = requests.get("https://ocremix.org/remixes/", headers=HEADERS, timeout=10)
            matches = re.findall(r'/remix/OCR(\d{5})', res.text)
            if matches: latest = max(int(m) for m in matches)
        except: pass
        files = [f for f in os.listdir(DOWNLOAD_DIR) if f.startswith("OCR")]
        local_ids = [int(re.match(r'OCR(\d{5})', f).group(1)) for f in files if re.match(r'OCR(\d{5})', f)]
        return {"latest_online": latest, "last_downloaded": max(local_ids) if local_ids else 0}

    def download(self, data):
        ids = []
        for part in data.get('ids', '').split(','):
            if '-' in part:
                s, e = part.split('-')
                ids.extend(range(int(s), int(e) + 1))
            elif part.strip().isdigit(): ids.append(int(part))
        
        missing_only = data.get('missing_only', False)
        existing = set(os.listdir(DOWNLOAD_DIR)) if missing_only else set()
        
        for idx, rid_int in enumerate(ids, 1):
            percent = int((idx / len(ids)) * 100)
            rid = f"OCR{rid_int:05d}"
            if missing_only and any(f.startswith(rid) for f in existing):
                yield {"line": f"[{rid}] Skipping existing.", "progress": percent}
                continue

            try:
                page = requests.get(f"https://ocremix.org/remix/{rid}", headers=HEADERS, timeout=10)
                soup = BeautifulSoup(page.text, "html.parser")
                link = next((a["href"] for a in soup.find_all("a", href=True) if "ocrmirror.org" in a["href"]), None)
                
                if link:
                    fname = os.path.basename(link)
                    yield {"line": f"[{rid}] Downloading: {fname}", "progress": percent}
                    with requests.get(link, headers=HEADERS, stream=True) as r:
                        with open(os.path.join(DOWNLOAD_DIR, f"{rid} - {fname}"), "wb") as f:
                            for chunk in r.iter_content(8192): f.write(chunk)
                else: yield {"line": f"<span class='text-orange-400'>[{rid}] No mirror.</span>", "progress": percent}
            except: yield {"line": f"<span class='text-red-400'>[{rid}] Failed.</span>", "progress": percent}
            time.sleep(0.5)
        yield {"line": "<b>--- Done ---</b>", "progress": 100}