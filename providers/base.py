from abc import ABC, abstractmethod
from typing import Any, Generator
import os

# ---------------------------------------------------------------------------
# Shared constants available to all providers
# ---------------------------------------------------------------------------

# Standard browser User-Agent headers used by every provider's HTTP requests.
# Import in your provider with:  from providers.base import BaseProvider, HEADERS
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


class BaseProvider(ABC):
    """
    Abstract base class for all download providers.

    To add a new provider, create a new .py file inside the ``providers/``
    directory and subclass ``BaseProvider``.  The app will discover and load
    it automatically on startup.

    Required class attributes
    -------------------------
    id : str
        Unique machine-readable identifier (e.g. "khinsider").
    name : str
        Human-readable display name (e.g. "KHInsider").
    description : str
        Short description shown in the UI.

    Two provider patterns are supported
    ------------------------------------
    Search-based (e.g. KHInsider):
        Override search() to return a list of results; the UI shows a search
        box and passes the chosen result's payload to download().

    ID/range-based (e.g. OCRemix):
        Leave search() as-is (returns [] and supports_search=False in
        get_info()); the UI renders a custom input form instead.
        Override download() to accept whatever fields that form submits.
    """

    # -- Subclasses must set these -------------------------------------------

    id: str = ""
    name: str = ""
    description: str = ""

    # -- Helpers -------------------------------------------------------------

    def get_path(self, subfolder: str = "") -> str:
        """
        Return the absolute path to the download directory for this provider,
        creating it if necessary.

        The root is taken from the DOWNLOAD_DIR environment variable
        (default: /downloads). If subfolder is given it is appended.
        """
        base = os.environ.get("DOWNLOAD_DIR", "/downloads")
        path = os.path.join(base, subfolder) if subfolder else base
        os.makedirs(path, exist_ok=True)
        return path

    # -- Optional overrides --------------------------------------------------

    def get_info(self) -> dict[str, Any]:
        """Return provider metadata shown in the UI."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            # Tells the frontend whether to show a search box or a custom form.
            "supports_search": type(self).search is not BaseProvider.search,
        }

    def search(self, query: str) -> list[dict[str, Any]]:
        """
        Search for albums / tracks matching query.

        The default implementation returns an empty list, meaning this provider
        does not support search-based discovery (e.g. OCRemix uses ID ranges).
        Override this in search-capable providers (e.g. KHInsider).

        Returns a list of result dicts. Each dict must contain at least:
            - name  (str) -- display name shown in the UI
            - url   (str) -- value passed back to download()
        """
        return []

    # -- Abstract interface (must implement) ---------------------------------

    @abstractmethod
    def download(self, payload: dict[str, Any]) -> Generator[dict[str, Any], None, None]:
        """
        Download the item described by payload and stream progress events.

        Yields dicts with at least:
            - line      (str) -- log message for the UI
            - progress  (int) -- 0-100 completion percentage

        The generator must yield a final event with progress == 100.
        Raise any exception to signal a fatal error; the caller catches it and
        forwards it to the frontend as a final error event.
        """
