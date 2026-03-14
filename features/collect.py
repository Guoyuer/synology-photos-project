"""Collect photos/videos matching persons, location, and date range."""

import os
import re
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

from features.download import download_item

ITEM_TYPE_NAMES = {0: "photo", 1: "video", 3: "live", 6: "motion"}


def _db_connect():
    return psycopg2.connect(
        host=os.getenv("NAS_DB_HOST", "192.168.1.169"),
        port=int(os.getenv("NAS_DB_PORT", "5432")),
        dbname=os.getenv("NAS_DB_NAME", "synofoto"),
        user=os.getenv("NAS_DB_USER", "postgres"),
    )


def resolve_persons(names: list[str]) -> dict[int, str]:
    """Resolve person name strings to {id: name}. Raises on no match."""
    conn = _db_connect()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM person WHERE name != ''")
    all_persons = cur.fetchall()
    conn.close()

    result = {}
    for query in names:
        q_lower = query.lower()
        # exact match first
        exact = [(pid, pname) for pid, pname in all_persons if pname.lower() == q_lower]
        if exact:
            result[exact[0][0]] = exact[0][1]
            continue
        # fuzzy contains match
        fuzzy = [(pid, pname) for pid, pname in all_persons if q_lower in pname.lower()]
        if len(fuzzy) == 1:
            result[fuzzy[0][0]] = fuzzy[0][1]
        elif len(fuzzy) == 0:
            raise ValueError(f"Person not found: '{query}'. Check 'python cli.py persons' for names.")
        else:
            suggestions = ", ".join(f"{n} (ID:{i})" for i, n in fuzzy[:5])
            raise ValueError(f"Ambiguous person '{query}'. Matches: {suggestions}")

    return result


def resolve_location(query: str) -> list[int]:
    """Resolve a location string to a list of geocoding IDs. Raises on no match."""
    conn = _db_connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT id_geocoding, country, first_level, second_level
        FROM geocoding_info
        WHERE lang = 0
    """)
    rows = cur.fetchall()
    conn.close()

    q = query.lower()
    matches = set()
    for gid, country, first, second in rows:
        if (country and q == country.lower()) or \
           (first and q == first.lower()) or \
           (second and q == second.lower()):
            matches.add(gid)

    if matches:
        return list(matches)

    # partial match fallback
    partial = set()
    for gid, country, first, second in rows:
        if any(q in (v or "").lower() for v in [country, first, second]):
            partial.add(gid)

    if not partial:
        raise ValueError(f"Location not found: '{query}'.")

    if len(partial) > 20:
        raise ValueError(
            f"'{query}' matches {len(partial)} regions — be more specific "
            f"(e.g. a country name or district)."
        )

    matched = [(c, f, s) for gid, c, f, s in rows if gid in partial]
    suggestions = ", ".join(f"{c}/{f}/{s}" for c, f, s in matched[:8])
    raise ValueError(f"Partial match for '{query}': {suggestions} — be more specific.")


def query_items(
    person_ids: list[int] = [],
    geocoding_ids: list[int] = [],
    from_ts: int | None = None,
    to_ts: int | None = None,
    item_types: list[int] = [],
    all_persons: bool = False,
    country: str | None = None,          # filter by country name
    first_level: str | None = None,      # filter by state/city (first_level)
    district: str | None = None,         # filter by district/second_level name
    concepts: list[str] = [],            # AI concept stems
    min_confidence: float = 0.7,
    cameras: list[str] = [],             # camera model names
    min_duration_s: int | None = None,   # minimum video duration in seconds
    min_width: int | None = None,        # minimum video width (e.g. 3840 for 4K)
    max_duration_s: int | None = None,   # maximum video duration (seconds)
    min_fps: int | None = None,          # minimum frame rate (fps, not millihertz)
    video_codecs: list[str] = [],        # ["hevc", "h264", "vp9"]
    has_audio: bool | None = None,       # True=must have audio, False=no audio
    has_gps: bool | None = None,         # True=must have GPS, False=no GPS
    limit: int | None = None,
    sort_desc: bool = False,
) -> list[dict]:
    """
    Core query function — single source of truth for all item filtering.

    Used by both the CLI (collect command) and the web API.

    Person modes:
      all_persons=False (default): items featuring ANY of the listed persons.
      all_persons=True:            items where ALL listed persons co-appear.
    """
    conn = _db_connect()
    cur = conn.cursor()

    conditions = ["1=1"]
    params = []
    person_filter = ""

    # --- Person filter ---
    if all_persons and person_ids:
        person_joins = ""
        person_params = []
        for i, pid in enumerate(person_ids):
            alias = f"mp{i}"
            person_joins += (
                f" JOIN many_unit_has_many_person {alias}"
                f" ON {alias}.id_unit = u.id AND {alias}.id_person = %s"
            )
            person_params.append(pid)
        params = person_params + params
        person_filter = person_joins
    elif person_ids:
        conditions.append(
            "EXISTS (SELECT 1 FROM many_unit_has_many_person mp "
            "WHERE mp.id_unit = u.id AND mp.id_person = ANY(%s))"
        )
        params.append(person_ids)

    # --- Location: explicit geocoding IDs (from resolve_location) ---
    if geocoding_ids:
        conditions.append("u.id_geocoding = ANY(%s)")
        params.append(geocoding_ids)

    # --- Location: country / first_level / district by name ---
    if country:
        loc_cond = "gi2.country = %s"
        loc_params = [country]
        if first_level:
            loc_cond += " AND gi2.first_level = %s"
            loc_params.append(first_level)
        if district:
            loc_cond += " AND gi2.second_level = %s"
            loc_params.append(district)
        conditions.append(
            f"EXISTS (SELECT 1 FROM geocoding_info gi2 "
            f"WHERE gi2.id_geocoding = u.id_geocoding AND gi2.lang = 0 AND {loc_cond})"
        )
        params.extend(loc_params)

    # --- Date range ---
    if from_ts is not None:
        conditions.append("u.takentime >= %s")
        params.append(from_ts)
    if to_ts is not None:
        conditions.append("u.takentime <= %s")
        params.append(to_ts)

    # --- Item type ---
    if item_types:
        conditions.append("u.item_type = ANY(%s)")
        params.append(item_types)

    # --- AI concepts ---
    if concepts:
        conditions.append(
            "EXISTS (SELECT 1 FROM many_unit_has_many_concept mc "
            "JOIN concept c ON c.id = mc.id_concept "
            "WHERE mc.id_unit = u.id AND c.stem = ANY(%s) AND mc.confidence >= %s)"
        )
        params.extend([concepts, min_confidence])

    # --- Camera ---
    if cameras:
        conditions.append(
            "EXISTS (SELECT 1 FROM metadata m WHERE m.id_unit = u.id AND m.camera = ANY(%s))"
        )
        params.append(cameras)

    # --- Video filters ---
    if min_duration_s is not None:
        conditions.append(
            "(u.item_type != 1 OR EXISTS "
            "(SELECT 1 FROM video_additional va2 WHERE va2.id_unit = u.id AND va2.duration >= %s))"
        )
        params.append(min_duration_s * 1000)
    if min_width is not None:
        conditions.append(
            "(u.item_type != 1 OR EXISTS "
            "(SELECT 1 FROM video_additional va3 WHERE va3.id_unit = u.id "
            "AND (va3.video_info->>'resolution_x')::int >= %s))"
        )
        params.append(min_width)
    if max_duration_s is not None:
        conditions.append(
            "(u.item_type != 1 OR EXISTS "
            "(SELECT 1 FROM video_additional va4 WHERE va4.id_unit = u.id AND va4.duration <= %s))"
        )
        params.append(max_duration_s * 1000)
    if min_fps is not None:
        conditions.append(
            "(u.item_type != 1 OR EXISTS (SELECT 1 FROM video_additional va5 WHERE va5.id_unit = u.id "
            "AND (CASE WHEN (va5.video_info->>'frame_rate_num')::int >= 1000 "
            "     THEN (va5.video_info->>'frame_rate_num')::int / 1000 "
            "     ELSE (va5.video_info->>'frame_rate_num')::int END) >= %s))"
        )
        params.append(min_fps)
    if video_codecs:
        conditions.append(
            "(u.item_type != 1 OR EXISTS (SELECT 1 FROM video_additional va6 WHERE va6.id_unit = u.id "
            "AND va6.video_info->>'video_codec' = ANY(%s)))"
        )
        params.append(video_codecs)
    if has_audio is True:
        conditions.append(
            "(u.item_type != 1 OR EXISTS (SELECT 1 FROM video_additional va7 WHERE va7.id_unit = u.id "
            "AND va7.audio_info->>'audio_codec' IS NOT NULL))"
        )
    elif has_audio is False:
        conditions.append(
            "(u.item_type != 1 OR EXISTS (SELECT 1 FROM video_additional va7 WHERE va7.id_unit = u.id "
            "AND (va7.audio_info IS NULL OR va7.audio_info->>'audio_codec' IS NULL)))"
        )
    if has_gps is True:
        conditions.append("u.id_geocoding IS NOT NULL")
    elif has_gps is False:
        conditions.append("u.id_geocoding IS NULL")

    sql = f"""
        SELECT DISTINCT
            u.id,
            u.filename,
            u.takentime,
            u.item_type,
            u.filesize,
            u.duplicate_hash,
            u.cache_key,
            (u.resolution->>'width')::int   AS width,
            (u.resolution->>'height')::int  AS height,
            va.duration,
            (va.video_info->>'resolution_x')::int  AS vres_x,
            (va.video_info->>'frame_rate_num')::int AS fps,
            va.video_info->>'video_codec'              AS video_codec,
            (va.video_info->>'video_bitrate')::bigint  AS video_bitrate,
            va.video_info->>'container_type'           AS container_type,
            va.audio_info->>'audio_codec'              AS audio_codec,
            (va.audio_info->>'channel')::int           AS audio_channel,
            (va.audio_info->>'frequency')::int         AS audio_frequency,
            gi.country,
            gi.first_level,
            gi.second_level AS district,
            f.name          AS folder_path,
            m.camera,
            m.lens,
            m.focal_length,
            m.aperture,
            m.iso,
            m.exposure_time,
            m.flash,
            m.description,
            m.latitude,
            m.longitude
        FROM unit u
        {person_filter}
        LEFT JOIN video_additional va ON va.id_unit = u.id
        LEFT JOIN geocoding_info gi  ON gi.id_geocoding = u.id_geocoding AND gi.lang = 0
        LEFT JOIN folder f           ON f.id = u.id_folder
        LEFT JOIN metadata m         ON m.id_unit = u.id
        WHERE {' AND '.join(conditions)}
        ORDER BY u.takentime {'DESC' if sort_desc else 'ASC'}
        {'LIMIT %s' if limit else ''}
    """

    if limit:
        params.append(limit)
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    seen = set()
    rows = []
    for row in cur.fetchall():
        d = dict(zip(cols, row))
        key = d.get("duplicate_hash") or d["id"]
        if key not in seen:
            seen.add(key)
            rows.append(d)
    conn.close()
    return rows


def _make_output_dir(persons: dict, location: str | None, from_date: str | None, to_date: str | None) -> str:
    parts = []
    if location:
        parts.append(re.sub(r"\s+", "-", location.lower()))
    if persons:
        for name in persons.values():
            parts.append(re.sub(r"\s+", "-", name.lower()))
    if from_date:
        parts.append(from_date)
    if to_date and to_date != from_date:
        parts.append(to_date)
    slug = "_".join(parts) or "collect"
    return str(Path("downloads") / slug)


def print_preview(items: list[dict], persons: dict, location: str | None,
                  from_date: str | None, to_date: str | None,
                  item_type: str | None, output_dir: str,
                  all_persons: bool = False) -> None:
    total_bytes = sum(r["filesize"] or 0 for r in items)
    total_mb = total_bytes / 1024 / 1024

    print("\n=== Collect Preview ===")
    if persons:
        sep = " ∩ " if all_persons else " + "
        persons_str = sep.join(f"{n} (ID:{i})" for i, n in persons.items())
        print(f"Persons:   {persons_str}")
    if location:
        print(f"Location:  {location}")
    if from_date or to_date:
        print(f"Date:      {from_date or '…'} → {to_date or '…'}")
    if item_type:
        print(f"Type:      {item_type}")
    print(f"\nFound {len(items)} items  ({total_mb:.1f} MB total)\n")

    if not items:
        print("No items matched. Try relaxing your filters.")
        return

    print(f"  {'#':>3}  {'Filename':<40}  {'Type':6}  {'Size':>8}  {'Duration':>8}  {'Res':>6}  District")
    print(f"  {'─'*3}  {'─'*40}  {'─'*6}  {'─'*8}  {'─'*8}  {'─'*6}  {'─'*12}")
    for i, r in enumerate(items, 1):
        type_s = ITEM_TYPE_NAMES.get(r["item_type"], "?")
        size_s = f"{r['filesize']/1024/1024:.1f}MB" if r["filesize"] else "?"
        dur_s = f"{r['duration']//1000}s" if r.get("duration") else ""
        res_s = f"{r['vres_x']}p" if r.get("vres_x") else (
            f"{r['width']}x{r['height']}" if r.get("width") else "")
        district = r.get("district") or ""
        print(f"  {i:>3}  {r['filename']:<40}  {type_s:6}  {size_s:>8}  {dur_s:>8}  {res_s:>6}  {district}")

    print(f"\nOutput: {output_dir}/")
    print(f"Run with --download to fetch all {len(items)} files ({total_mb:.1f} MB).")


def collect(
    photos,                        # Photos API instance (for download)
    persons: list[str] | None = None,
    location: str | None = None,
    from_date: str | None = None,  # "YYYY-MM-DD"
    to_date: str | None = None,
    item_type: str | None = None,  # "photo", "video", "live", "motion"
    output_dir: str | None = None,
    download: bool = False,
    limit: int | None = None,
    all_persons: bool = False,     # True = all must co-appear; False = any
) -> bool:
    # Validate at least one filter
    if not persons and not location and not from_date and not to_date:
        print("❌ Specify at least one filter: --persons, --location, or --from/--to")
        return False

    # Resolve persons
    resolved_persons = {}
    if persons:
        try:
            resolved_persons = resolve_persons(persons)
        except ValueError as e:
            print(f"❌ {e}")
            return False

    # Resolve location
    geocoding_ids = []
    if location:
        try:
            geocoding_ids = resolve_location(location)
        except ValueError as e:
            print(f"❌ {e}")
            return False

    # Parse dates to unix timestamps
    from_ts = to_ts = None
    if from_date:
        from_ts = int(datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    if to_date:
        # end of day
        to_ts = int(datetime.strptime(to_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()) + 86399

    # Map type string to item_type int
    type_map = {"photo": 0, "video": 1, "live": 3, "motion": 6}
    item_type_int = type_map.get(item_type) if item_type else None

    # Query
    items = query_items(
        person_ids=list(resolved_persons.keys()),
        geocoding_ids=geocoding_ids,
        from_ts=from_ts,
        to_ts=to_ts,
        item_types=[item_type_int] if item_type_int is not None else [],
        all_persons=all_persons,
        limit=limit,
    )

    # Auto-name output dir
    if not output_dir:
        output_dir = _make_output_dir(resolved_persons, location, from_date, to_date)

    print_preview(items, resolved_persons, location, from_date, to_date, item_type, output_dir, all_persons)

    if not download or not items:
        return True

    # Download
    print(f"\n=== Downloading {len(items)} files to {output_dir}/ ===\n")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    success, failed = 0, 0
    for i, item in enumerate(items, 1):
        filename = item["filename"]
        dest = Path(output_dir) / filename
        # Handle duplicate filenames
        if dest.exists():
            stem, suffix = Path(filename).stem, Path(filename).suffix
            filename = f"{stem}_{item['id']}{suffix}"
            dest = Path(output_dir) / filename

        ok = download_item(photos, item["id"], filename, output_dir)
        status = "✅" if ok else "❌"
        size_s = f"{item['filesize']/1024/1024:.1f}MB" if item["filesize"] else ""
        print(f"  {status} {i}/{len(items)}  {item['filename']:<40}  {size_s}")
        if ok:
            success += 1
        else:
            failed += 1

    print(f"\nDownloaded: {success}   Failed: {failed}")
    return success > 0
