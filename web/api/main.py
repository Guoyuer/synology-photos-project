"""FastAPI backend for Synology Photos web UI."""

import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

import json
import mimetypes

import orjson
import psycopg2
import psycopg2.extras
import psycopg2.pool
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

from features.collect import query_items, ITEM_TYPE_NAMES

app = FastAPI(title="Synology Photos API")

app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=1)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


_db_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=2, maxconn=10,
    host=os.getenv("NAS_DB_HOST", "192.168.1.169"),
    port=int(os.getenv("NAS_DB_PORT", "5432")),
    dbname=os.getenv("NAS_DB_NAME", "synofoto"),
    user=os.getenv("NAS_DB_USER", "postgres"),
    cursor_factory=psycopg2.extras.RealDictCursor,
)


@contextmanager
def db():
    conn = _db_pool.getconn()
    try:
        yield conn
    finally:
        _db_pool.putconn(conn)


# ---------------------------------------------------------------------------
# Reference data cache (persons, locations, concepts, cameras rarely change)
# ---------------------------------------------------------------------------

_ref_cache: dict[str, tuple[float, list]] = {}   # key -> (expires_at, data)
_REF_TTL = 300  # 5 minutes


def _cached_ref(key: str, sql: str) -> list:
    now = time.monotonic()
    entry = _ref_cache.get(key)
    if entry and entry[0] > now:
        return entry[1]
    with db() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        rows = [dict(r) for r in cur.fetchall()]
    _ref_cache[key] = (now + _REF_TTL, rows)
    return rows


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
    return _cached_ref("persons", """
        SELECT p.id, p.name, pic.item_count
        FROM person p
        JOIN person_item_count pic ON pic.id_person = p.id
        WHERE p.name != '' AND p.hidden = false
        ORDER BY pic.item_count DESC
    """)


@app.get("/api/locations")
def list_locations():
    return _cached_ref("locations", """
        SELECT DISTINCT gi.country, gi.first_level, gi.second_level,
               count(DISTINCT u.id) as item_count
        FROM geocoding_info gi
        JOIN unit u ON u.id_geocoding = gi.id_geocoding
        WHERE gi.lang = 0 AND gi.country IS NOT NULL
        GROUP BY gi.country, gi.first_level, gi.second_level
        ORDER BY gi.country, gi.first_level, gi.second_level
    """)


@app.get("/api/concepts")
def list_concepts():
    return _cached_ref("concepts", """
        SELECT c.id, c.stem, count(mc.id_unit) as usage_count
        FROM concept c
        JOIN many_unit_has_many_concept mc ON mc.id_concept = c.id
        WHERE c.hidden = false
        GROUP BY c.id, c.stem
        ORDER BY usage_count DESC
    """)


@app.get("/api/cameras")
def list_cameras():
    return _cached_ref("cameras", """
        SELECT camera, count(*) as item_count
        FROM metadata
        WHERE camera IS NOT NULL AND camera != ''
        GROUP BY camera
        ORDER BY item_count DESC
    """)


# ---------------------------------------------------------------------------
# Collect — delegates entirely to features/collect.py
# ---------------------------------------------------------------------------

class CollectRequest(BaseModel):
    person_ids: list[int] = []
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
    max_duration: Optional[int] = None
    min_fps: Optional[int] = None
    video_codecs: list[str] = []
    has_audio: Optional[bool] = None
    has_gps: Optional[bool] = None
    person_count: Optional[str] = None   # 'none' | '1' | '2+'
    limit: Optional[int] = None
    sort_desc: bool = False


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
        max_duration_s=req.max_duration,
        min_fps=req.min_fps,
        video_codecs=req.video_codecs,
        has_audio=req.has_audio,
        has_gps=req.has_gps,
        person_count=req.person_count,
        limit=req.limit,
        sort_desc=req.sort_desc,
    )

    for item in items:
        item["type_name"] = ITEM_TYPE_NAMES.get(item["item_type"], "?")
        item["taken_iso"] = datetime.fromtimestamp(item["takentime"]).isoformat() if item["takentime"] else None

    total_bytes = sum(r.get("filesize") or 0 for r in items)
    payload = {
        "items": items,
        "count": len(items),
        "total_mb": round(total_bytes / 1024 / 1024, 1),
    }
    return Response(content=orjson.dumps(payload), media_type="application/json")


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


def _stream_motion_video(folder_name: str, filename: str):
    """Stream the MP4 embedded at the end of a Google Motion Photo JPEG.

    Scans incoming chunks for the last 'ftyp' box header, then pipes from that
    offset onward — avoids buffering the entire file in memory.
    """
    photos = get_session()
    fs_path = f"/home/Photos{folder_name}/{filename}"
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
    buffer = b""
    found = False
    for chunk in resp.iter_content(65536):
        if found:
            yield chunk
        else:
            buffer += chunk
            idx = buffer.rfind(b'ftyp')
            if idx >= 4:
                found = True
                yield buffer[idx - 4:]
                buffer = b""


@app.get("/api/media/{item_id}")
def stream_media(item_id: int, as_video: bool = False):
    with db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.filename, u.item_type, f.name AS folder_name,
                   comp.companion_filename, comp.companion_folder
            FROM unit u
            JOIN folder f ON f.id = u.id_folder
            LEFT JOIN live_additional la_m ON la_m.id_unit = u.id AND u.item_type = 3
            LEFT JOIN LATERAL (
                SELECT comp_u.filename AS companion_filename, f_comp.name AS companion_folder
                FROM live_additional la_c
                JOIN unit comp_u ON comp_u.id = la_c.id_unit
                                AND comp_u.id != u.id
                                AND (comp_u.filename ILIKE '%%.mov' OR comp_u.filename ILIKE '%%.mp4')
                JOIN folder f_comp ON f_comp.id = comp_u.id_folder
                WHERE la_c.grouping_key = la_m.grouping_key
                LIMIT 1
            ) comp ON la_m.id_unit IS NOT NULL
            WHERE u.id = %s
        """, (item_id,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    if as_video:
        if row["item_type"] == 3 and row["companion_filename"] and row["companion_folder"]:
            return _filestation_stream(row["companion_folder"], row["companion_filename"], "video/mp4")
        if row["item_type"] == 6:
            return StreamingResponse(_stream_motion_video(row["folder_name"], row["filename"]), media_type="video/mp4")

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
# Item metadata (persons + concepts) — used by MetaPanel
# ---------------------------------------------------------------------------

@app.get("/api/meta/{item_id}")
def item_meta(item_id: int):
    with db() as conn:
        cur = conn.cursor()

        # Full item details (EXIF, video, folder — everything the info panel needs)
        cur.execute("""
            SELECT f.name AS folder_path,
                   m.camera, m.lens, m.focal_length, m.aperture, m.iso,
                   m.exposure_time, m.flash, m.orientation, m.description,
                   m.latitude, m.longitude,
                   va.duration,
                   (va.video_info->>'resolution_x')::int  AS vres_x,
                   (va.video_info->>'resolution_y')::int  AS vres_y,
                   (va.video_info->>'frame_rate_num')::int AS fps,
                   va.video_info->>'video_codec'              AS video_codec,
                   (va.video_info->>'video_bitrate')::bigint  AS video_bitrate,
                   va.video_info->>'container_type'           AS container_type,
                   va.audio_info->>'audio_codec'              AS audio_codec,
                   (va.audio_info->>'channel')::int           AS audio_channel,
                   (va.audio_info->>'frequency')::int         AS audio_frequency,
                   (va.audio_info->>'audio_bitrate')::bigint  AS audio_bitrate
            FROM unit u
            LEFT JOIN folder f           ON f.id = u.id_folder
            LEFT JOIN metadata m         ON m.id_unit = u.id
            LEFT JOIN video_additional va ON va.id_unit = u.id
            WHERE u.id = %s
        """, (item_id,))
        detail = dict(cur.fetchone() or {})

        cur.execute("""
            SELECT p.name
            FROM many_unit_has_many_person mp
            JOIN person p ON p.id = mp.id_person
            WHERE mp.id_unit = %s AND p.name != ''
            ORDER BY p.name
        """, (item_id,))
        detail["persons"] = [r["name"] for r in cur.fetchall()]

        cur.execute("""
            SELECT c.stem, mc.confidence
            FROM many_unit_has_many_concept mc
            JOIN concept c ON c.id = mc.id_concept
            WHERE mc.id_unit = %s AND c.hidden = false
            ORDER BY mc.confidence DESC
            LIMIT 20
        """, (item_id,))
        detail["concepts"] = [{"stem": r["stem"], "confidence": round(r["confidence"], 2)} for r in cur.fetchall()]

    return detail


# ---------------------------------------------------------------------------
# Thumbnail proxy
# ---------------------------------------------------------------------------

@app.get("/api/thumbnail/{item_id}/{cache_key}")
def thumbnail(item_id: int, cache_key: str, size: str = "sm"):
    size_map = {"sm": "sm", "md": "m", "lg": "xl"}
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
    resp = requests.get(url, params=params, verify=photos.session._verify, timeout=15)
    content_type = resp.headers.get("Content-Type", "image/jpeg")
    if "text/html" in content_type:
        raise HTTPException(status_code=404, detail="Thumbnail not available")
    return Response(content=resp.content, media_type=content_type)
