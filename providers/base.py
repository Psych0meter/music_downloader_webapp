import os

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class BaseProvider:
    id = "base"         # Used for URLs and internal logic
    name = "Base"       # Used for the UI Tab name
    
    def get_info(self):
        return {}

    def search(self, query):
        return []

    def download(self, data):
        yield {"line": "Not implemented.", "progress": 100}