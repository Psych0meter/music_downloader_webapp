import os
from abc import ABC, abstractmethod
from typing import Any, Generator

# ---------------------------------------------------------------------------
# Shared constants available to all providers
# ---------------------------------------------------------------------------

# Standard browser User-Agent headers for plain requests (non-Cloudflare sites).
# Import with:  from providers.base import BaseProvider, HEADERS
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

    To add a new provider, create:
      providers/<id>.py
      templates/providers/<id>.html

    The app discovers and loads providers automatically on startup.
    See PROVIDER_GUIDE.md for full documentation.

    Required class attributes
    -------------------------
    id : str
        Unique machine-readable identifier. MUST match the filename:
        ``khinsider.py`` → ``id = "khinsider"``
    name : str
        Human-readable display name shown in the tab bar.
    description : str
        One-line description shown in the UI.

    Two provider patterns
    ---------------------
    Search-based (e.g. KHInsider):
        Override ``search()``; the UI shows a search box and passes the
        chosen result to ``download()``.

    ID/range-based (e.g. OCRemix):
        Leave ``search()`` as-is; the UI renders a custom form instead.
    """

    id: str = ""
    name: str = ""
    description: str = ""
    # Optional: set this in your provider to save downloads into a subfolder of
    # DOWNLOAD_DIR by default.  The user can still override it from the UI.
    # Example:  default_subfolder = "KHInsider"
    default_subfolder: str = ""

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def get_path(self, subfolder: str = "") -> str:
        """
        Return the absolute download directory for this provider, creating it
        if necessary.

        Resolution order:
          1. ``subfolder`` argument (from the UI folder input — treated as a
             subfolder *name*, never a full path)
          2. ``self.default_subfolder`` class attribute
          3. ``DOWNLOAD_DIR`` root (default: ``/downloads``)

        The subfolder value is sanitised: leading slashes and path separators
        are stripped so a user cannot accidentally escape DOWNLOAD_DIR.
        """
        base = os.environ.get("DOWNLOAD_DIR", "/downloads")
        # Use UI input if provided, else fall back to the provider default
        effective = subfolder.strip() or self.default_subfolder.strip()
        if effective:
            # Strip any leading separators — treat it as a name, not a path
            effective = effective.lstrip("/\\")
            path = os.path.join(base, effective)
        else:
            path = base
        os.makedirs(path, exist_ok=True)
        return path

    # -------------------------------------------------------------------------
    # Optional overrides
    # -------------------------------------------------------------------------

    def get_info(self) -> dict[str, Any]:
        """
        Return provider metadata sent to the frontend via ``/api/info/<id>``.

        Always contains: id, name, description, supports_search, default_path.
        Override to add provider-specific fields (stats, latest IDs, etc.) —
        call ``super().get_info()`` first and update the returned dict.
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            # Tells the frontend whether to show a search box or a custom form.
            "supports_search": type(self).search is not BaseProvider.search,
            # Convenience: the frontend can pre-fill the folder input from this.
            "default_path": os.environ.get("DOWNLOAD_DIR", "/downloads"),
            "default_subfolder": self.default_subfolder,
        }

    def search(self, query: str) -> list[dict[str, Any]]:
        """
        Search for items matching *query*.

        Default returns ``[]`` (provider does not support search).
        Override in search-capable providers.

        Each result dict must contain at least:
          - ``name``  (str) — display text
          - ``url``   (str) — passed to :meth:`download` as ``payload["url"]``
        """
        return []

    # -------------------------------------------------------------------------
    # Abstract interface
    # -------------------------------------------------------------------------

    @abstractmethod
    def download(
        self, payload: dict[str, Any]
    ) -> Generator[dict[str, Any], None, None]:
        """
        Download the item described by *payload* and yield progress events.

        Each yielded dict must contain:
          - ``line``      (str) — log message for the UI (HTML is allowed)
          - ``progress``  (int) — completion percentage 0-100

        The **final** event must have ``progress == 100``.
        Unhandled exceptions are caught by the app and forwarded to the
        frontend as a final error event.
        """
