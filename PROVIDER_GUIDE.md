# 🔌 Provider Development Guide

Providers are self-contained drop-in add-ons. Each provider is exactly **two files**:

```
providers/your_source.py          ← Python: scraping + download logic
templates/providers/your_source.html  ← HTML: UI for this provider
```

Drop both files in, restart the app — the provider appears automatically in the UI.  
Remove both files, restart — it's gone. No other files need to be touched.

---

## Quickstart

### 1. Copy the skeleton files

```bash
cp providers/_skeleton.py        providers/mysource.py
cp templates/providers/_skeleton.html  templates/providers/mysource.html
```

### 2. Edit the Python file

Open `providers/mysource.py` and fill in:
- `id` — short unique string, **must match the filename** (`mysource.py` → `id = "mysource"`)
- `name` — display name shown in the tab bar
- `description` — one-line description
- `default_subfolder` — optional subfolder inside `DOWNLOAD_DIR` for this provider's downloads (e.g. `"KHInsider"` → saves to `DOWNLOAD_DIR/KHInsider/`). The user can still override it from the UI.
- `search()` — optional, for search-based providers (KHInsider-style)
- `download()` — required, streams progress events to the UI

### 3. Edit the HTML template

Open `templates/providers/mysource.html` and build the UI for your provider.  
The template has access to Alpine.js for reactivity and Tailwind CSS for styling.

### 4. Restart the app

```bash
# Bare Python
systemctl restart music-downloader   # Proxmox LXC
# or
python3 app.py                        # local dev

# Docker
docker compose restart
```

Your provider tab appears in the UI immediately.

---

## Provider patterns

### Pattern A — Search-based (like KHInsider)

User types a query → results list → user picks one → download starts.

1. Implement `search(query)` returning a list of `{"name": ..., "url": ...}` dicts
2. Implement `download(payload)` where `payload["url"]` is the chosen URL
3. In your HTML template, call `/api/search/your_id` and display results

### Pattern B — ID/range-based (like OCRemix)

User enters IDs or a range → download starts directly.

1. **Skip** `search()` — the base class default returns `[]` and sets `supports_search: false`
2. Implement `download(payload)` accepting whatever fields your HTML form submits
3. In your HTML template, dispatch `start-download` directly with your form values

---

## Key rules

| Rule | Why |
|------|-----|
| `id` must match the filename | `app.py` maps `provider.id` → `templates/providers/<id>.html` |
| Files starting with `_` are ignored | Keeps `_skeleton.py` out of the live app — use it as a template only |
| Final `download()` event must have `progress: 100` | The UI progress bar relies on this to stop |
| Alpine state function must be uniquely named | `khState()`, `ocrState()`, `skeletonState()` — never `state()` |
| Dispatch `start-download` with `provider` + `payload` | The main app wires this to the SSE download endpoint |
| `get_path(subfolder)` for all file I/O | Respects `DOWNLOAD_DIR` env var and `default_subfolder`; creates dir if needed |
| Set `default_subfolder` to organise downloads | e.g. `default_subfolder = "KHInsider"` → saves to `DOWNLOAD_DIR/KHInsider/` |

---

## Removing a provider

```bash
rm providers/mysource.py
rm templates/providers/mysource.html
systemctl restart music-downloader   # or docker compose restart
```

The tab disappears from the UI on the next page load.

---

## Full file checklist

When creating a new provider called `mysource`:

- [ ] `providers/mysource.py` — Python logic
- [ ] `templates/providers/mysource.html` — UI template
- [ ] `id = "mysource"` in the Python class matches both filenames exactly
- [ ] `download()` always yields a final `{"progress": 100}` event
- [ ] Alpine state function named `mysourceState()` (or similar unique name)
- [ ] Tested locally before submitting a PR
