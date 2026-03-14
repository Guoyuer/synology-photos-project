# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A two-part tool for browsing and downloading photos from a Synology NAS running Synology Photos:

1. **CLI** — `cli.py` + `features/` — command-line tool for querying and downloading
2. **Web UI** — `web/api/main.py` (FastAPI) + `web/frontend/` (React) — browser-based photo search and download

## Commands

### Python (CLI + backend)
```bash
# Run the CLI
python cli.py --help
python cli.py persons
python cli.py collect --persons "Alice" --from 2024-01-01 --download

# Run the FastAPI backend (from repo root)
cd web/api && uvicorn main:app --reload --port 8000 --reload-dir ../..

# Run Python tests (from repo root)
pytest tests/test_collect_unit.py        # unit tests for query_items SQL builder
pytest tests/test_api_unit.py            # unit tests for FastAPI endpoints (all mocked)
pytest tests/test_integration.py        # integration tests (requires live DB + NAS)
pytest tests/ -k "not integration"      # skip integration tests
```

### Frontend
```bash
cd web/frontend
npm install
npm run dev          # Vite dev server on :5173, proxies /api/* to localhost:8000
npm run build        # TypeScript check + production build
npm run test:e2e     # Playwright E2E tests (requires: npm run dev running on :5174)
```

The Playwright config expects the dev server on port **5174** (run with `-- --port 5174`), not the default 5173. E2E tests mock all API routes via `page.route()` — no backend needed.

## Architecture

### The key design insight: direct DB + Photos API session hybrid

The Synology Photos API doesn't support complex multi-filter queries (persons + location + date + concepts + camera simultaneously). So this project **queries Synology's internal Postgres DB directly** for search, while using the **Synology API session** only for file serving (thumbnails, downloads, streaming).

- **DB**: `synofoto` Postgres (connection params from `.env`, defaults to `192.168.1.169:5432`)
- **Photos API session**: authenticated via `synology-api` library, cached to `~/.synology_photos_session`
- **`features/collect.py::query_items()`** is the single source of truth for all item filtering — used by both the CLI and the FastAPI `/api/collect` endpoint

### Key DB tables
- `unit` — every photo/video (columns: `id`, `filename`, `takentime`, `item_type`, `filesize`, `resolution`, `id_folder`, `id_geocoding`, `cache_key`, `duplicate_hash`)
- `folder` — folder records; `folder.name` is the NAS path like `/Photos/NewYork`
- `video_additional` — video metadata (`duration` in ms, `video_info` JSONB with `resolution_x`, `frame_rate_num`)
- `geocoding_info` — location data (`country`, `first_level`, `second_level`), `lang=0` for English
- `many_unit_has_many_person` — person↔photo join
- `many_unit_has_many_concept` — AI concept↔photo join with `confidence` score
- `live_additional` — live photo grouping; links a HEIC/JPG unit to its companion MOV via `grouping_key`
- `metadata` — EXIF data including `camera`, `latitude`, `longitude`

### item_type values
- `0` = photo, `1` = video, `3` = live photo (HEIC + companion .MOV), `6` = motion photo (Google Pixel .MP.jpg with embedded MP4)

### Special media serving (web/api/main.py)
- **Thumbnails**: proxied via `SYNO.Foto.Thumbnail` API using the `cache_key` from DB
- **Live photo video (type=3)**: companion `.MOV` is a non-major unit (rejected by `SYNO.Foto.Download`). Fetched via `SYNO.FileStation.Download` at path `/home/Photos{folder.name}/{filename}`
- **Motion photo video (type=6)**: MP4 is embedded at the end of the JPEG. Extracted by `data.rfind(b'ftyp')` — everything from `idx-4` onward is a valid MP4
- **Regular photos/videos**: streamed via `SYNO.Foto.Download` with `download_type=source`
- **`_filestation_get()`** uses `photos.request_data(response_json=False)` (synology-api built-in, handles auth) for buffered fetches, and raw `requests.get(stream=True)` for streaming (library doesn't support stream mode)

### Session management
`session_manager.py` caches `sid` + `syno_token` to `~/.synology_photos_session` (JSON, 24h TTL). On load, it validates by calling `photos.get_userinfo()`. `manage_session.py` contains `show_status()` which is imported by `cli.py session status`.

### Frontend state flow
`App.tsx` holds all state: `persons/locations/concepts/cameras` (reference data, loaded once), `result` (current search results), `cart` (selected items for download). `FilterPanel` → `onSearch` → FastAPI `/api/collect` → `ResultsGrid`.

`ResultsGrid` uses `@tanstack/react-virtual` to render only visible rows — thumbnails are never fetched for off-screen items. Column count is derived from container width via a `ResizeObserver`.

Shared formatting utilities (`fmt`, `fmtDur`, `TYPE_BADGE`) live in `src/utils.ts`.

### Environment variables (`.env`)
```
NAS_IP, NAS_PORT, NAS_USERNAME, NAS_PASSWORD
NAS_SECURE, NAS_CERT_VERIFY, NAS_DSM_VERSION
NAS_DB_HOST, NAS_DB_PORT, NAS_DB_NAME, NAS_DB_USER
```
