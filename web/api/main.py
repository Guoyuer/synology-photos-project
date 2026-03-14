"""FastAPI backend for Synology Photos web UI."""

import os
import sys
from datetime import datetime, timezone
from typing import Optional

import json
import mimetypes
import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

from features.collect import query_items, ITEM_TYPE_NAMES

app = FastAPI(title="Synology Photos API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def db():
    return psycopg2.connect(
        host=os.getenv("NAS_DB_HOST", "192.168.1.169"),
        port=int(os.getenv("NAS_DB_PORT", "5432")),
        dbname=os.getenv("NAS_DB_NAME", "synofoto"),
        user=os.getenv("NAS_DB_USER", "postgres"),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


_photos_session = None


def get_session():
    global _photos_session
    if _photos_session is None:
        from session_manager import get_photos_api
        _photos_session, _ = get_photos_api(
            nas_ip=os.getenv("NAS_IP"),
            nas_port=os.getenv("NAS_PORT"),
            nas_username=os.getenv("NAS_USERNAME"),
            nas_password=os.getenv("NAS_PASSWORD"),
            nas_secure=os.getenv("NAS_SECURE", "False").lower() == "true",
            nas_cert_verify=os.getenv("NAS_CERT_VERIFY", "False").lower() == "true",
            nas_dsm_version=int(os.getenv("NAS_DSM_VERSION", "7")),
            use_cache=True,
        )
    return _photos_session


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

@app.get("/api/persons")
def list_persons():
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.name, pic.item_count
        FROM person p
        JOIN person_item_count pic ON pic.id_person = p.id
        WHERE p.name != '' AND p.hidden = false
        ORDER BY pic.item_count DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


@app.get("/api/locations")
def list_locations():
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT gi.country, gi.first_level, gi.second_level,
               count(DISTINCT u.id) as item_count
        FROM geocoding_info gi
        JOIN unit u ON u.id_geocoding = gi.id_geocoding
        WHERE gi.lang = 0 AND gi.country IS NOT NULL
        GROUP BY gi.country, gi.first_level, gi.second_level
        ORDER BY gi.country, gi.first_level, gi.second_level
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


@app.get("/api/concepts")
def list_concepts():
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.stem, count(mc.id_unit) as usage_count
        FROM concept c
        JOIN many_unit_has_many_concept mc ON mc.id_concept = c.id
        WHERE c.hidden = false
        GROUP BY c.id, c.stem
        ORDER BY usage_count DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


@app.get("/api/cameras")
def list_cameras():
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT camera, count(*) as item_count
        FROM metadata
        WHERE camera IS NOT NULL AND camera != ''
        GROUP BY camera
        ORDER BY item_count DESC
        LIMIT 50
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Collect — delegates entirely to features/collect.py
# ---------------------------------------------------------------------------

class CollectRequest(BaseModel):
    person_ids: list[int] = []
    all_persons: bool = False
    country: Optional[str] = None
    first_level: Optional[str] = None
    district: Optional[str] = None
    from_date: Optional[str] = None   # YYYY-MM-DD
    to_date: Optional[str] = None
    item_types: list[int] = []
    concepts: list[str] = []
    min_confidence: float = 0.7
    cameras: list[str] = []
    min_duration: Optional[int] = None   # seconds
    min_width: Optional[int] = None
    limit: Optional[int] = None
    offset: int = 0


@app.post("/api/collect")
def collect(req: CollectRequest):
    from_ts = (
        int(datetime.strptime(req.from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
        if req.from_date else None
    )
    to_ts = (
        int(datetime.strptime(req.to_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()) + 86399
        if req.to_date else None
    )

    items = query_items(
        person_ids=req.person_ids,
        all_persons=req.all_persons,
        country=req.country,
        first_level=req.first_level,
        district=req.district,
        from_ts=from_ts,
        to_ts=to_ts,
        item_types=req.item_types,
        concepts=req.concepts,
        min_confidence=req.min_confidence,
        cameras=req.cameras,
        min_duration_s=req.min_duration,
        min_width=req.min_width,
        limit=req.limit,
        offset=req.offset,
    )

    for item in items:
        item["type_name"] = ITEM_TYPE_NAMES.get(item["item_type"], "?")
        item["taken_iso"] = datetime.fromtimestamp(item["takentime"]).isoformat() if item["takentime"] else None

    total_bytes = sum(r.get("filesize") or 0 for r in items)
    return {
        "items": items,
        "count": len(items),
        "total_mb": round(total_bytes / 1024 / 1024, 1),
    }


# ---------------------------------------------------------------------------
# Bulk download (streams Synology zip)
# ---------------------------------------------------------------------------

class DownloadRequest(BaseModel):
    item_ids: list[int]


@app.post("/api/download")
def download_files(req: DownloadRequest):
    photos = get_session()
    url = photos.session._base_url + "entry.cgi"
    data = {
        "api": "SYNO.Foto.Download",
        "method": "download",
        "version": "2",
        "item_id": json.dumps(req.item_ids),
        "download_type": "source",
        "force_download": "true",
        "_sid": photos.session.sid,
    }
    resp = requests.post(
        url,
        params={"SynoToken": photos.session.syno_token},
        data=data,
        verify=photos.session._verify,
        stream=True,
        timeout=600,
    )
    content_type = resp.headers.get("Content-Type", "application/zip")
    disposition = resp.headers.get("Content-Disposition", "attachment; filename=photos.zip")
    return StreamingResponse(
        resp.iter_content(chunk_size=65536),
        media_type=content_type,
        headers={"Content-Disposition": disposition},
    )


# ---------------------------------------------------------------------------
# Full-resolution media stream (for lightbox preview)
# ---------------------------------------------------------------------------

def _filestation_get(folder_name: str, filename: str, stream: bool = False):
    """Fetch a file via FileStation API. Returns a raw requests.Response."""
    photos = get_session()
    fs_path = f"/home/Photos{folder_name}/{filename}"
    # Use synology-api's request_data which handles _sid and auth token automatically.
    # For streaming we fall back to raw requests since request_data doesn't support stream=True.
    if stream:
        resp = requests.get(
            photos.session._base_url + "entry.cgi",
            params={
                "api": "SYNO.FileStation.Download",
                "method": "download",
                "version": "2",
                "path": json.dumps([fs_path]),
                "mode": "open",
                "SynoToken": photos.session.syno_token,
                "_sid": photos.session.sid,
            },
            verify=photos.session._verify,
            stream=True,
            timeout=300,
        )
    else:
        resp = photos.request_data(
            api_name="SYNO.FileStation.Download",
            api_path="entry.cgi",
            req_param={"method": "download", "version": "2",
                       "path": json.dumps([fs_path]), "mode": "open"},
            method="get",
            response_json=False,
        )
    return resp


def _filestation_stream(folder_name: str, filename: str, content_type: str):
    """Stream a file from Synology via FileStation API (for companion videos)."""
    resp = _filestation_get(folder_name, filename, stream=True)
    return StreamingResponse(resp.iter_content(chunk_size=65536), media_type=content_type)


@app.get("/api/media/{item_id}")
def stream_media(item_id: int, as_video: bool = False):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.filename, u.item_type, f.name AS folder_name
        FROM unit u JOIN folder f ON f.id = u.id_folder
        WHERE u.id = %s
    """, (item_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Item not found")

    if as_video:
        if row["item_type"] == 3:  # live photo — find companion MOV/MP4 unit
            cur.execute("""
                SELECT u.filename, f.name AS folder_name
                FROM live_additional la
                JOIN unit u ON u.id = la.id_unit
                JOIN folder f ON f.id = u.id_folder
                WHERE la.grouping_key = (
                    SELECT grouping_key FROM live_additional WHERE id_unit = %s
                )
                AND u.id != %s
                AND (u.filename ILIKE %s OR u.filename ILIKE %s)
                LIMIT 1
            """, (item_id, item_id, '%.mov', '%.mp4'))
            companion = cur.fetchone()
            conn.close()
            if companion:
                return _filestation_stream(companion["folder_name"], companion["filename"], "video/mp4")

        elif row["item_type"] == 6:  # motion photo — extract embedded MP4 from JPEG
            folder_name, filename = row["folder_name"], row["filename"]
            conn.close()
            data = _filestation_get(folder_name, filename).content
            # Google Motion Photo embeds an MP4 at the end of the JPEG.
            # The last ftyp box marks the start of the MP4 container.
            idx = data.rfind(b'ftyp')
            if idx >= 4:
                return Response(content=data[idx - 4:], media_type="video/mp4")

        else:
            conn.close()
    else:
        conn.close()

    # Default: stream source via SYNO.Foto.Download
    photos = get_session()
    url = photos.session._base_url + "entry.cgi"
    resp = requests.post(
        url,
        params={"SynoToken": photos.session.syno_token},
        data={
            "api": "SYNO.Foto.Download",
            "method": "download",
            "version": "2",
            "item_id": json.dumps([item_id]),
            "download_type": "source",
            "force_download": "true",
            "_sid": photos.session.sid,
        },
        verify=photos.session._verify,
        stream=True,
        timeout=300,
    )
    content_type, _ = mimetypes.guess_type(row["filename"])
    return StreamingResponse(
        resp.iter_content(chunk_size=65536),
        media_type=content_type or "application/octet-stream",
    )


# ---------------------------------------------------------------------------
# Thumbnail proxy
# ---------------------------------------------------------------------------

@app.get("/api/thumbnail/{item_id}")
def thumbnail(item_id: int, size: str = "sm"):
    size_map = {"sm": "sm", "md": "m", "lg": "xl"}

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT cache_key FROM unit WHERE id = %s", (item_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    cache_key = row["cache_key"]

    photos = get_session()
    url = photos.session._base_url + "entry.cgi"
    params = {
        "api": "SYNO.Foto.Thumbnail",
        "method": "get",
        "version": "2",
        "id": item_id,
        "type": "unit",
        "size": size_map.get(size, "sm"),
        "cache_key": f"{item_id}_{cache_key}",
        "SynoToken": photos.session.syno_token,
        "_sid": photos.session.sid,
    }
    resp = requests.get(url, params=params, verify=photos.session._verify, stream=True, timeout=15)
    content_type = resp.headers.get("Content-Type", "image/jpeg")
    return StreamingResponse(resp.iter_content(chunk_size=8192), media_type=content_type)
