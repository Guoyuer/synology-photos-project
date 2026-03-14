

# Synofoto Database Query Guide

Direct PostgreSQL access to the `synofoto` database on the NAS.

**Connection:**
```python
import psycopg2
conn = psycopg2.connect(host='192.168.1.169', port=5432, dbname='synofoto', user='postgres')
```

---

## Key Tables

### `unit` — every photo/video file (67,504 rows)
The central table. One row per file.

| Column | Type | Notes |
|--------|------|-------|
| `id` | int | Primary key |
| `filename` | text | Original filename |
| `filesize` | bigint | Bytes |
| `takentime` | bigint | Unix timestamp (seconds) when photo was taken |
| `item_type` | smallint | **0**=photo, **1**=video, **3**=live photo, **6**=motion photo |
| `type` | smallint | **0**=personal space, **1**=shared space |
| `resolution` | json | `{"width": 3840, "height": 2160}` |
| `id_geocoding` | int | FK → `geocoding.id` (NULL if no GPS) |
| `id_folder` | int | FK → `folder.id` |
| `id_item` | int | FK → `item.id` |

### `metadata` — EXIF data (one row per unit)
| Column | Type | Notes |
|--------|------|-------|
| `id_unit` | int | FK → `unit.id` |
| `latitude` | float | GPS latitude |
| `longitude` | float | GPS longitude |
| `camera` | text | e.g. "Pixel 7 Pro" |
| `lens` | text | |
| `focal_length` | text | |
| `iso` | text | |
| `aperture` | text | |
| `rating` | smallint | Star rating |
| `description` | text | Caption |

### `video_additional` — video metadata
| Column | Type | Notes |
|--------|------|-------|
| `id_unit` | int | FK → `unit.id` |
| `duration` | bigint | Milliseconds |
| `video_info` | json | `container_type`, `resolution_x`, `resolution_y`, `frame_rate_num`, `video_codec`, `video_bitrate` |
| `audio_info` | json | Audio codec info |

Sample `video_info`:
```json
{"container_type": "mp4", "frame_bitrate": 61105187, "frame_rate_num": 60,
 "resolution_x": 3840, "resolution_y": 2160, "video_codec": "hevc"}
```

### `person` — named people (5,273 rows)
| Column | Type | Notes |
|--------|------|-------|
| `id` | int | e.g. 88 = Yuer Guo, 97 = Yi Zhang |
| `name` | text | Display name (empty string for unnamed faces) |
| `hidden` | bool | Hidden from UI |

### `many_unit_has_many_person` — person ↔ unit mapping (5,305 rows)
| Column | Notes |
|--------|-------|
| `id_unit` | Unit the person appears in |
| `id_person` | Person ID |

### `face` — individual face detections (21,970 rows)
| Column | Type | Notes |
|--------|------|-------|
| `id_unit` | int | Which photo/video |
| `id_person` | int | Which person (can be NULL = unidentified) |
| `bounding_box` | json | `{x, y, width, height}` as fractions 0–1 |
| `score` | int | Confidence score |
| `is_manual` | bool | True if user manually tagged |

### `geocoding` + `geocoding_info` — location (874 geocoding regions)
`geocoding` stores the hierarchy. `geocoding_info` stores human-readable names.

| `geocoding_info` column | Notes |
|-------------------------|-------|
| `id_geocoding` | FK → `geocoding.id` |
| `country` | e.g. `"Singapore"`, `"China"` |
| `first_level` | State/territory e.g. `"Singapore"` |
| `second_level` | City/district e.g. `"Changi"` |
| `lang` | Language code (0 = default) |

`unit.id_geocoding` links each file to a geocoding region.

### `concept` + `many_unit_has_many_concept` — AI tags (354 concepts)
AI-detected scene/object labels with confidence scores.

Key concepts: `child`, `selfie`, `food`, `beach`, `mountain`, `ocean`, `sunset`,
`dog`, `cat`, `restaurant`, `street`, `cityscape`, `night_view`, `fireworks`,
`wedding`, `birthday`, `sport`, `swimming`, `hiking`, `travel`...

Full list of 354 concepts includes food types, animals, sports, instruments, scenes, objects.

| `many_unit_has_many_concept` column | Notes |
|-------------------------------------|-------|
| `id_unit` | Unit |
| `id_concept` | Concept |
| `confidence` | 0.0–1.0 decimal |

### `address` — reverse-geocoded text addresses (1,426,950 rows)
Human-readable address strings for each unit.

| Column | Notes |
|--------|-------|
| `id_unit` | FK → `unit.id` |
| `value` | e.g. `"Singapore"`, `"Marina Bay"` |
| `admin` | Admin level (1=country, 2=state, 3=city...) |
| `level` | Hierarchy depth |
| `lang` | Language (0=default) |

---

## Common Query Patterns

### Filter by person (single)
```sql
SELECT u.id, u.filename, u.takentime, u.item_type
FROM unit u
JOIN many_unit_has_many_person mp ON mp.id_unit = u.id
WHERE mp.id_person = 88  -- Yuer Guo
ORDER BY u.takentime DESC;
```

### Filter by multiple persons (co-appearance — both in same photo)
```sql
SELECT u.id, u.filename, u.takentime
FROM unit u
JOIN many_unit_has_many_person mp1 ON mp1.id_unit = u.id AND mp1.id_person = 88
JOIN many_unit_has_many_person mp2 ON mp2.id_unit = u.id AND mp2.id_person = 97
ORDER BY u.takentime DESC;
```

### Filter by location (country)
```sql
SELECT u.id, u.filename, u.takentime
FROM unit u
JOIN geocoding_info gi ON gi.id_geocoding = u.id_geocoding
WHERE gi.country = 'Singapore' AND gi.lang = 0
ORDER BY u.takentime DESC;
```

### Filter by location (city/district)
```sql
WHERE gi.country = 'Singapore' AND gi.second_level = 'Changi' AND gi.lang = 0
```

### Filter by GPS bounding box
```sql
SELECT u.id, u.filename
FROM unit u
JOIN metadata m ON m.id_unit = u.id
WHERE m.latitude BETWEEN 1.22 AND 1.47
  AND m.longitude BETWEEN 103.6 AND 104.0;  -- Singapore bounds
```

### Filter by date range
```sql
WHERE u.takentime BETWEEN 1748736000 AND 1749340800
-- Convert: SELECT extract(epoch from '2025-06-01'::date)
```

### Filter by type
```sql
WHERE u.item_type = 0   -- photos only
WHERE u.item_type = 1   -- videos only
WHERE u.item_type = 3   -- live photos only
WHERE u.item_type IN (1, 6)  -- videos + motion photos
```

### Filter by video duration
```sql
JOIN video_additional va ON va.id_unit = u.id
WHERE va.duration > 5000   -- longer than 5 seconds
```

### Filter by video resolution (4K only)
```sql
JOIN video_additional va ON va.id_unit = u.id
WHERE (va.video_info->>'resolution_x')::int >= 3840
```

### Filter by AI concept
```sql
JOIN many_unit_has_many_concept mc ON mc.id_unit = u.id
JOIN concept c ON c.id = mc.id_concept
WHERE c.stem = 'food' AND mc.confidence > 0.8
```

### Full vlog collect query — persons + location + date + type
```sql
SELECT
    u.id,
    u.filename,
    u.takentime,
    u.filesize,
    u.item_type,
    u.resolution,
    va.duration,
    va.video_info
FROM unit u
-- Person 1
JOIN many_unit_has_many_person mp1 ON mp1.id_unit = u.id AND mp1.id_person = 88
-- Person 2
JOIN many_unit_has_many_person mp2 ON mp2.id_unit = u.id AND mp2.id_person = 97
-- Location
JOIN geocoding_info gi ON gi.id_geocoding = u.id_geocoding AND gi.lang = 0
-- Video metadata (LEFT JOIN to keep photos too)
LEFT JOIN video_additional va ON va.id_unit = u.id
WHERE gi.country = 'Singapore'
  AND u.takentime BETWEEN 1748736000 AND 1749340800  -- 2025-06-01 to 2025-06-07
  AND u.item_type IN (1, 6)  -- videos only
ORDER BY u.takentime;
```

### Lookup person ID by name
```sql
SELECT id, name FROM person WHERE lower(name) LIKE '%yuer%';
```

### Lookup geocoding IDs for a country
```sql
SELECT DISTINCT id_geocoding, first_level, second_level
FROM geocoding_info
WHERE country = 'Singapore' AND lang = 0;
```

### Find all AI concepts in a photo
```sql
SELECT c.stem, mc.confidence
FROM many_unit_has_many_concept mc
JOIN concept c ON c.id = mc.id_concept
WHERE mc.id_unit = 90885
ORDER BY mc.confidence DESC;
```

### Items without GPS
```sql
WHERE u.id_geocoding IS NULL
```

### Search by address text (reverse geocoded)
```sql
JOIN address a ON a.id_unit = u.id
WHERE a.value ILIKE '%Marina Bay%' AND a.lang = 0
```

---

## Useful Helper Queries

### Count items per person (named only)
```sql
SELECT p.id, p.name, pic.item_count
FROM person p
JOIN person_item_count pic ON pic.id_person = p.id
WHERE p.name != ''
ORDER BY pic.item_count DESC;
```

### Date range summary for a person
```sql
SELECT
    date_trunc('month', to_timestamp(u.takentime)) AS month,
    count(*) AS count
FROM unit u
JOIN many_unit_has_many_person mp ON mp.id_unit = u.id
WHERE mp.id_person = 88
GROUP BY 1 ORDER BY 1;
```

### Top countries by item count
```sql
SELECT gi.country, count(*) AS cnt
FROM unit u
JOIN geocoding_info gi ON gi.id_geocoding = u.id_geocoding AND gi.lang = 0
GROUP BY gi.country
ORDER BY cnt DESC;
```

### Find duplicate files
```sql
SELECT duplicate_hash, count(*), array_agg(filename)
FROM unit
GROUP BY duplicate_hash
HAVING count(*) > 1;
```

---

## Notes

- **`takentime`** is Unix seconds. Convert with `to_timestamp(takentime)` in SQL or `datetime.fromtimestamp()` in Python.
- **`item_type`**: 0=photo, 1=video, 3=live photo, 4=unknown, 6=motion photo (Google Pixel). `type` column is 0=personal, 1=shared.
- **`geocoding_info.lang = 0`** is the default language. Always filter `lang = 0` to avoid duplicate rows.
- **`many_unit_has_many_person`** only covers items where Synology has identified a person — face recognition must have completed. Videos may have fewer entries than photos.
- **`concept` confidence** ranges 0.0–1.0. Use `> 0.7` for reliable matches, `> 0.9` for high confidence.
- **`address`** table has millions of rows (reverse-geocoded strings). More flexible than `geocoding_info` for text search but slower — prefer `geocoding_info` for country/region filtering.
- **No writes** — treat as read-only. DSM manages all writes via the SynologyPhotos package.
