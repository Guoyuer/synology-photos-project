"""FastAPI backend for Synology Photos web UI."""

import os
import sys
from datetime import datetime, timezone
from typing import Optional

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

app = FastAPI(title="Synology Photos API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ITEM_TYPE_NAMES = {0: "photo", 1: "video", 3: "live", 6: "motion"}


def db():
    return psycopg2.connect(
        host=os.getenv("NAS_DB_HOST", "192.168.1.169"),
        port=int(os.getenv("NAS_DB_PORT", "5432")),
        dbname=os.getenv("NAS_DB_NAME", "synofoto"),
        user=os.getenv("NAS_DB_USER", "postgres"),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def nas_session():
    """Get authenticated Photos session for thumbnails/downloads."""
    from session_manager import get_photos_api
    photos, _ = get_photos_api(
        nas_ip=os.getenv("NAS_IP"),
        nas_port=os.getenv("NAS_PORT"),
        nas_username=os.getenv("NAS_USERNAME"),
        nas_password=os.getenv("NAS_PASSWORD"),
        nas_secure=os.getenv("NAS_SECURE", "False").lower() == "true",
        nas_cert_verify=os.getenv("NAS_CERT_VERIFY", "False").lower() == "true",
        nas_dsm_version=int(os.getenv("NAS_DSM_VERSION", "7")),
        use_cache=True,
    )
    return photos


# Cache the session
_photos_session = None


def get_session():
    global _photos_session
    if _photos_session is None:
        _photos_session = nas_session()
    return _photos_session


# ---------------------------------------------------------------------------
# Reference data endpoints
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
# Collect / search
# ---------------------------------------------------------------------------

class CollectRequest(BaseModel):
    person_ids: list[int] = []
    all_persons: bool = False          # True = intersection, False = union
    country: Optional[str] = None
    district: Optional[str] = None
    from_date: Optional[str] = None   # YYYY-MM-DD
    to_date: Optional[str] = None
    item_types: list[int] = []        # empty = all
    concepts: list[str] = []          # concept stems
    min_confidence: float = 0.7
    cameras: list[str] = []
    min_duration: Optional[int] = None   # seconds
    min_width: Optional[int] = None
    limit: Optional[int] = None


@app.post("/api/collect")
def collect(req: CollectRequest):
    conn = db()
    cur = conn.cursor()

    conditions = ["1=1"]
    params = []
    person_joins = ""
    person_params = []

    # --- Person filter ---
    if req.person_ids:
        if req.all_persons:
            for i, pid in enumerate(req.person_ids):
                alias = f"mp{i}"
                person_joins += (
                    f" JOIN many_unit_has_many_person {alias}"
                    f" ON {alias}.id_unit = u.id AND {alias}.id_person = %s"
                )
                person_params.append(pid)
        else:
            conditions.append(
                "EXISTS (SELECT 1 FROM many_unit_has_many_person mp "
                "WHERE mp.id_unit = u.id AND mp.id_person = ANY(%s))"
            )
            params.append(req.person_ids)

    # --- Location ---
    if req.country:
        conditions.append(
            "EXISTS (SELECT 1 FROM geocoding_info gi "
            "WHERE gi.id_geocoding = u.id_geocoding AND gi.lang = 0 "
            "AND gi.country = %s" +
            (" AND gi.second_level = %s" if req.district else "") +
            ")"
        )
        params.append(req.country)
        if req.district:
            params.append(req.district)

    # --- Date range ---
    if req.from_date:
        ts = int(datetime.strptime(req.from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
        conditions.append("u.takentime >= %s")
        params.append(ts)
    if req.to_date:
        ts = int(datetime.strptime(req.to_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()) + 86399
        conditions.append("u.takentime <= %s")
        params.append(ts)

    # --- Item type ---
    if req.item_types:
        conditions.append("u.item_type = ANY(%s)")
        params.append(req.item_types)

    # --- Concepts ---
    if req.concepts:
        conditions.append("""
            EXISTS (
                SELECT 1 FROM many_unit_has_many_concept mc
                JOIN concept c ON c.id = mc.id_concept
                WHERE mc.id_unit = u.id
                  AND c.stem = ANY(%s)
                  AND mc.confidence >= %s
            )
        """)
        params.append(req.concepts)
        params.append(req.min_confidence)

    # --- Camera ---
    if req.cameras:
        conditions.append(
            "EXISTS (SELECT 1 FROM metadata m WHERE m.id_unit = u.id AND m.camera = ANY(%s))"
        )
        params.append(req.cameras)

    # --- Video filters (applied post-join) ---
    video_conditions = []
    if req.min_duration:
        video_conditions.append(f"va.duration >= {req.min_duration * 1000}")
    if req.min_width:
        video_conditions.append(f"(va.video_info->>'resolution_x')::int >= {req.min_width}")

    video_join = "LEFT JOIN video_additional va ON va.id_unit = u.id"
    if video_conditions:
        conditions.append("(" + " AND ".join(video_conditions) + " OR u.item_type != 1)")

    # Person JOIN params come first (appear before WHERE in SQL)
    all_params = person_params + params

    sql = f"""
        SELECT DISTINCT
            u.id,
            u.filename,
            u.takentime,
            u.item_type,
            u.filesize,
            u.duplicate_hash,
            (u.resolution->>'width')::int  AS width,
            (u.resolution->>'height')::int AS height,
            va.duration,
            (va.video_info->>'resolution_x')::int AS vres_x,
            (va.video_info->>'frame_rate_num')::int AS fps,
            gi.country,
            gi.second_level AS district,
            m.camera,
            m.latitude,
            m.longitude
        FROM unit u
        {person_joins}
        {video_join}
        LEFT JOIN geocoding_info gi ON gi.id_geocoding = u.id_geocoding AND gi.lang = 0
        LEFT JOIN metadata m ON m.id_unit = u.id
        WHERE {' AND '.join(conditions)}
        ORDER BY u.takentime
        {'LIMIT ' + str(req.limit) if req.limit else ''}
    """

    cur.execute(sql, all_params)
    raw = cur.fetchall()
    conn.close()

    # Deduplicate by duplicate_hash
    seen = set()
    items = []
    for r in raw:
        row = dict(r)
        key = row.get("duplicate_hash") or row["id"]
        if key not in seen:
            seen.add(key)
            row["type_name"] = ITEM_TYPE_NAMES.get(row["item_type"], "?")
            row["taken_iso"] = datetime.fromtimestamp(row["takentime"]).isoformat() if row["takentime"] else None
            items.append(row)

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
    syno_size = size_map.get(size, "sm")
    photos = get_session()
    url = photos.session._base_url + "entry.cgi"
    params = {
        "api": "SYNO.Foto.Thumbnail",
        "method": "get",
        "version": "2",
        "id": item_id,
        "type": "unit",
        "size": syno_size,
        "cache_key": "1",
        "SynoToken": photos.session.syno_token,
        "_sid": photos.session.sid,
    }
    resp = requests.get(url, params=params, verify=photos.session._verify, stream=True, timeout=15)
    content_type = resp.headers.get("Content-Type", "image/jpeg")
    return StreamingResponse(resp.iter_content(chunk_size=8192), media_type=content_type)
