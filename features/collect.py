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

    # show what was found and ask user to pick
    conn2 = _db_connect()
    cur2 = conn2.cursor()
    cur2.execute(
        "SELECT DISTINCT country, first_level, second_level FROM geocoding_info "
        "WHERE id_geocoding = ANY(%s) AND lang = 0",
        (list(partial),)
    )
    suggestions = ", ".join(
        f"{r[0]}/{r[1]}/{r[2]}" for r in cur2.fetchall()[:8]
    )
    conn2.close()
    raise ValueError(f"Partial match for '{query}': {suggestions} — be more specific.")


def query_items(
    person_ids: list[int],
    geocoding_ids: list[int],
    from_ts: int | None,
    to_ts: int | None,
    item_type: int | None,
    all_persons: bool = False,
) -> list[dict]:
    """
    Run the SQL query and return matched items.

    all_persons=False (default): items featuring ANY of the listed persons (UNION).
    all_persons=True:            items where ALL listed persons co-appear (intersection).
    """
    conn = _db_connect()
    cur = conn.cursor()

    conditions = ["1=1"]
    params = []

    # Location filter
    if geocoding_ids:
        conditions.append("u.id_geocoding = ANY(%s)")
        params.append(geocoding_ids)

    # Date range
    if from_ts is not None:
        conditions.append("u.takentime >= %s")
        params.append(from_ts)
    if to_ts is not None:
        conditions.append("u.takentime <= %s")
        params.append(to_ts)

    # Type filter
    if item_type is not None:
        conditions.append("u.item_type = %s")
        params.append(item_type)

    if all_persons and person_ids:
        # Intersection: one JOIN per person — all must appear in same unit
        person_joins = ""
        person_params = []
        for i, pid in enumerate(person_ids):
            alias = f"mp{i}"
            person_joins += (
                f" JOIN many_unit_has_many_person {alias}"
                f" ON {alias}.id_unit = u.id AND {alias}.id_person = %s"
            )
            person_params.append(pid)
        # Person JOIN params come before WHERE params in SQL
        params = person_params + params
        person_filter = person_joins
    elif person_ids:
        # Union: any of the listed persons
        conditions.append("EXISTS ("
            "SELECT 1 FROM many_unit_has_many_person mp "
            "WHERE mp.id_unit = u.id AND mp.id_person = ANY(%s)"
            ")")
        params.append(person_ids)
        person_filter = ""
    else:
        person_filter = ""

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
            gi.country,
            gi.second_level AS district
        FROM unit u
        {person_filter}
        LEFT JOIN video_additional va ON va.id_unit = u.id
        LEFT JOIN geocoding_info gi ON gi.id_geocoding = u.id_geocoding AND gi.lang = 0
        WHERE {' AND '.join(conditions)}
        ORDER BY u.takentime
    """

    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    seen_hash = set()
    seen_id = set()
    rows = []
    for row in cur.fetchall():
        d = dict(zip(cols, row))
        dedup_key = d.get("duplicate_hash") or d["id"]
        if dedup_key not in seen_hash and d["id"] not in seen_id:
            seen_hash.add(dedup_key)
            seen_id.add(d["id"])
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
        item_type=item_type_int,
        all_persons=all_persons,
    )

    if limit:
        items = items[:limit]

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
