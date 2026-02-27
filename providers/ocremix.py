import os, re, time, glob, requests
from bs4 import BeautifulSoup
from providers.base import BaseProvider, DOWNLOAD_DIR, HEADERS

class OCRemixProvider(BaseProvider):
    id = "ocremix"
    name = "OCRemix"

    def get_info(self):
        latest = None
        try:
            matches = re.findall(r'/remix/OCR(\d{5})', requests.get("https://ocremix.org/remixes/", headers=HEADERS, timeout=10).text)
            if matches: latest = max(int(m) for m in matches)
        except: pass
        files = glob.glob(os.path.join(DOWNLOAD_DIR, "OCR*"))
        local_ids = [int(re.match(r'OCR(\d{5})', os.path.basename(f)).group(1)) for f in files if re.match(r'OCR(\d{5})', os.path.basename(f))]
        return {"latest_online": latest or "Unknown", "last_downloaded": max(local_ids) if local_ids else 0}

    def download(self, data):
        ids = sorted(set(int(p) for p in re.findall(r'\d+', data.get('ids', '')))) # simplified parsing
        missing_only = data.get('missing_only', False)
        
        existing = set(os.listdir(DOWNLOAD_DIR)) if missing_only else set()
        
        for index, remix_id_int in enumerate(ids, 1):
            percent = int((index / len(ids)) * 100)
            remix_id = f"OCR{remix_id_int:05d}"

            if missing_only and any(f.startswith(remix_id) for f in existing):
                yield {"line": f"[{remix_id}] Skipping existing.", "progress": percent}
                continue

            try:
                page = requests.get(f"https://ocremix.org/remix/{remix_id}", headers=HEADERS, timeout=10)
                download_url = next((a["href"] for a in BeautifulSoup(page.text, "html.parser").find_all("a", href=True) if "ocrmirror.org" in a["href"]), None)
                
                if download_url:
                    filepath = os.path.join(DOWNLOAD_DIR, f"{remix_id} - {os.path.basename(download_url)}")
                    with requests.get(download_url, headers=HEADERS, stream=True) as r:
                        r.raise_for_status()
                        with open(filepath, "wb") as f:
                            for chunk in r.iter_content(8192): f.write(chunk)
                    yield {"line": f"<span class='text-emerald-400'>[{remix_id}] OK.</span>", "progress": percent}
                else:
                    yield {"line": f"<span class='text-orange-400'>[{remix_id}] No link.</span>", "progress": percent}
            except Exception as e:
                yield {"line": f"<span class='text-red-400'>[{remix_id}] Failed.</span>", "progress": percent}
            
            time.sleep(0.5)
        yield {"line": "<span class='text-blue-400 font-bold'>--- Done ---</span>", "progress": 100}