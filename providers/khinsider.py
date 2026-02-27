import os, re, requests
from urllib.parse import unquote
from bs4 import BeautifulSoup
from providers.base import BaseProvider, HEADERS

class KHInsiderProvider(BaseProvider):
    id = "khinsider"
    name = "KHInsider"

    def _sanitize(self, name, is_album=False):
        name = unquote(name)
        if is_album:
            name = re.sub(r'_?MP3_Soundtracks_for_FREE.*$|\s+MP3\s+Soundtracks\s+for\s+FREE.*$', '', name, flags=re.IGNORECASE)
        return re.sub(r'[\\/*?:"<>|]', "", name).replace(" ", "_")

    def search(self, query):
        res = requests.get(f"https://downloads.khinsider.com/search?search={query.replace(' ', '+')}", headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        results = []
        for row in soup.select('.albumList tr'):
            cols = row.find_all('td')
            if len(cols) > 1 and cols[1].find('a'):
                link = cols[1].find('a')
                results.append({'album': link.text.strip(), 'url': f"https://downloads.khinsider.com{link['href']}"})
        return results

    def download(self, data):
        preferred_ext = data.get('format', '.flac')
        custom_folder = data.get('folder', '')
        base_path = self.get_path(custom_folder)
        
        yield {"line": "Analyzing album...", "progress": 0}
        try:
            res = requests.get(data.get('url'), headers=HEADERS)
            soup = BeautifulSoup(res.text, 'html.parser')
            album_title = self._sanitize(soup.find("title").text.replace(" - Download", "").strip(), is_album=True)
            song_links = sorted(list(set(f"https://downloads.khinsider.com{a['href']}" for a in soup.find_all('a', href=True) if '/game-soundtracks/album/' in a['href'] and a['href'].endswith(('.mp3', '.flac', '.m4a')))))
            
            album_path = os.path.join(base_path, album_title)
            os.makedirs(album_path, exist_ok=True)

            total = len(song_links)
            for idx, page_url in enumerate(song_links, 1):
                page_soup = BeautifulSoup(requests.get(page_url, headers=HEADERS).text, 'html.parser')
                audio_links = [a['href'] for a in page_soup.find_all('a', href=True) if a['href'].endswith(('.mp3', '.flac', '.m4a'))]
                if not audio_links: continue
                
                target_url = next((l for l in audio_links if l.endswith(preferred_ext)), audio_links[0])
                file_name = self._sanitize(os.path.basename(target_url))
                
                yield {"line": f"Track {idx}/{total}: {file_name}", "progress": int((idx/total)*100)}
                
                with requests.get(target_url, headers=HEADERS, stream=True) as r:
                    with open(os.path.join(album_path, file_name), 'wb') as f:
                        for chunk in r.iter_content(65536): f.write(chunk)
            yield {"line": "<span class='text-emerald-400'>=== FINISHED ===</span>", "progress": 100}
        except Exception as e:
            yield {"line": f"<span class='text-red-400'>Error: {str(e)}</span>", "progress": 100}