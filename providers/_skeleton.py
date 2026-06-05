import os
from typing import Any, Generator
from providers.base import BaseProvider, HEADERS

# Uncomment the import that suits your target site:
#
# Standard HTTP (no Cloudflare):
#   import requests
#
# Cloudflare bypass:
#   from curl_cffi import requests
#   _session = requests.Session(impersonate="chrome")


class SkeletonProvider(BaseProvider):
    # -------------------------------------------------------------------------
    # id MUST match the filename exactly:  _skeleton.py → id = "_skeleton"
    # Rename both files when creating a real provider.
    # -------------------------------------------------------------------------
    id = "_skeleton"
    name = "My Source"
    description = "Short description shown in the provider tab"

    # -------------------------------------------------------------------------
    # OPTIONAL — delete this method for ID/range-based providers (like OCRemix)
    # -------------------------------------------------------------------------
    def search(self, query: str) -> list[dict[str, Any]]:
        """
        Return search results for *query*.

        Each dict MUST contain:
          - "name"  (str) — text shown in the results table
          - "url"   (str) — passed to download() when the user clicks Download

        Extra keys are forwarded to the frontend as-is.
        """
        # Example:
        # res = requests.get("https://example.com/search", params={"q": query}, headers=HEADERS)
        # return [{"name": r["title"], "url": r["link"]} for r in res.json()]
        return []

    # -------------------------------------------------------------------------
    # OPTIONAL — override to expose extra data to the frontend info panel
    # -------------------------------------------------------------------------
    def get_info(self) -> dict[str, Any]:
        info = super().get_info()
        # info["my_stat"] = "some value"
        return info

    # -------------------------------------------------------------------------
    # REQUIRED
    # -------------------------------------------------------------------------
    def download(self, payload: dict[str, Any]) -> Generator[dict[str, Any], None, None]:
        """
        Download the item described by *payload* and yield progress events.

        Each yielded dict must contain:
          "line"     (str) — log message shown in the UI (HTML allowed)
          "progress" (int) — completion percentage 0–100

        The FINAL event must have progress == 100.
        Unhandled exceptions are caught by the app and sent as a final error event.
        """
        dest = self.get_path(payload.get("folder", ""))

        yield {"line": "Starting download...", "progress": 0}

        # ---- your download logic here ----------------------------------------
        # url = payload["url"]
        # r = requests.get(url, headers=HEADERS, stream=True)
        # r.raise_for_status()
        # with open(os.path.join(dest, "filename.mp3"), "wb") as f:
        #     for chunk in r.iter_content(8192):
        #         f.write(chunk)
        # ----------------------------------------------------------------------

        yield {"line": "<span class='text-emerald-400'>=== FINISHED ===</span>", "progress": 100}
