import os
import re

ROOT_DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}

class BaseProvider:
    id = "base"
    name = "Base"

    def get_default_path(self):
        """Returns Env Var (e.g. KHINSIDER_PATH) or fallback to ID."""
        env_key = f"{self.id.upper()}_PATH"
        return os.getenv(env_key, self.id)

    def get_path(self, custom_folder=None):
        """Priority: UI Input > Env Var > Default ID."""
        subfolder = custom_folder.strip() if custom_folder and custom_folder.strip() else self.get_default_path()
        # Sanitize to prevent directory traversal
        subfolder = re.sub(r'[\\/*?:"<>|]', "", subfolder)
        path = os.path.join(ROOT_DOWNLOAD_DIR, subfolder)
        os.makedirs(path, exist_ok=True)
        return path

    def get_info(self):
        """Passes configuration to the frontend."""
        return {"default_path": self.get_default_path()}

    def search(self, query):
        return []

    def download(self, data):
        yield {"line": "Not implemented", "progress": 100}