"""FastAPI backend for Synology Photos web UI."""

import os
import sys
from datetime import datetime, timezone
from typing import Optional

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
# Thumbnail proxy
# ---------------------------------------------------------------------------

@app.get("/api/thumbnail/{item_id}")
def thumbnail(item_id: int, size: str = "sm"):
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
        "cache_key": "1",
        "SynoToken": photos.session.syno_token,
        "_sid": photos.session.sid,
    }
    resp = requests.get(url, params=params, verify=photos.session._verify, stream=True, timeout=15)
    content_type = resp.headers.get("Content-Type", "image/jpeg")
    return StreamingResponse(resp.iter_content(chunk_size=8192), media_type=content_type)
