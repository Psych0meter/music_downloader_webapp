import importlib.util
import inspect
import json
import logging
import os
import sys
import threading
from collections import deque

from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    stream_with_context,
)

from providers.base import BaseProvider

load_dotenv()

# ---------------------------------------------------------------------------
# Logging — dual handler: stdout + in-memory ring buffer for the web log view
# ---------------------------------------------------------------------------


class WebLogHandler(logging.Handler):
    def __init__(self, capacity=200):
        super().__init__()
        self.buffer = deque(maxlen=capacity)

    def emit(self, record):
        self.buffer.append(self.format(record))


log_handler = WebLogHandler()
log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout), log_handler],
)
logger = logging.getLogger("MediaVault")

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)

PROVIDERS: dict[str, BaseProvider] = {}

# Serializes actual download work across requests/threads. Providers like
# KHInsider keep per-thread scraping sessions, but two downloads racing each
# other still isn't something we want to allow (duplicate file writes,
# unpredictable ordering in the log view). Acquired non-blocking so a second
# request fails fast with a clear message instead of silently queueing.
download_lock = threading.Lock()


def load_providers() -> None:
    """
    Dynamically discover and load every BaseProvider subclass found in the
    providers/ directory.  Individual provider import errors are caught and
    logged so a single broken provider does not take the whole app down.
    """
    # Use an absolute path so the app works regardless of the working directory
    providers_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "providers")
    os.makedirs(providers_dir, exist_ok=True)

    for filename in sorted(os.listdir(providers_dir)):
        if not filename.endswith(".py") or filename in ("__init__.py", "base.py") or filename.startswith("_"):
            continue

        module_name = filename[:-3]
        filepath = os.path.join(providers_dir, filename)

        try:
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseProvider) and obj is not BaseProvider:
                    instance = obj()
                    PROVIDERS[instance.id] = instance
                    logger.info("Plugin loaded: %s", instance.id)

        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load provider '%s': %s", module_name, exc)


load_providers()

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    return render_template("index.html", providers=list(PROVIDERS.values()))


@app.route("/logs")
def logs_page():
    return render_template("logs.html")


# -- System ------------------------------------------------------------------


@app.route("/api/system/logs")
def get_system_logs():
    return jsonify({"logs": list(log_handler.buffer)})


@app.route("/api/health")
def health():
    """Simple liveness probe used by Docker / Proxmox health checks."""
    return jsonify({"status": "ok", "providers": list(PROVIDERS.keys())})


# -- Provider info / search --------------------------------------------------


@app.route("/api/info/<provider_id>")
def provider_info(provider_id: str):
    provider = PROVIDERS.get(provider_id)
    if provider is None:
        return jsonify({"error": "Provider not found"}), 404
    return jsonify(provider.get_info())


@app.route("/api/search/<provider_id>", methods=["POST"])
def search(provider_id: str):
    provider = PROVIDERS.get(provider_id)
    if provider is None:
        return jsonify({"error": "Provider not found"}), 404

    query = (request.json or {}).get("query", "").strip()
    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400

    try:
        results = provider.search(query)
        return jsonify({"results": results})
    except Exception as exc:  # noqa: BLE001
        logger.error("Search error in provider '%s': %s", provider_id, exc)
        return jsonify({"error": str(exc)}), 500


# -- Download (SSE stream) ---------------------------------------------------


@app.route("/api/download/<provider_id>", methods=["POST"])
def download(provider_id: str):
    provider = PROVIDERS.get(provider_id)
    if provider is None:
        return jsonify({"error": "Provider not found"}), 404

    payload = request.json or {}

    def generate():
        if not download_lock.acquire(blocking=False):
            logger.warning("Rejected download for '%s': another download is already running", provider_id)
            yield (
                "data: "
                + json.dumps(
                    {
                        "line": "<span class='text-red-400'>"
                        "Another download is already in progress. Please wait for it to finish."
                        "</span>",
                        "progress": 100,
                    }
                )
                + "\n\n"
            )
            return
        try:
            for log_data in provider.download(payload):
                yield f"data: {json.dumps(log_data)}\n\n"
        except Exception as exc:  # noqa: BLE001
            logger.error("Download error in provider '%s': %s", provider_id, exc)
            yield f"data: {json.dumps({'line': f'Critical Error: {exc}', 'progress': 100})}\n\n"
        finally:
            download_lock.release()

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            # Prevent buffering by proxies / nginx
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
        },
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    # threaded=True so /api/health, /logs, etc. stay responsive while a
    # download is streaming — the download_lock above still limits actual
    # download work to one at a time.
    app.run(host="0.0.0.0", port=port, debug=debug, threaded=True)
