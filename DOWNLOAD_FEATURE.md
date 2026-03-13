# Photo Download Feature - Implementation Status

## Summary

✅ **Working:** List photos of a specific person
⚠️ **Partially Working:** Download API endpoint exists but requires authentication fix

## What Works

### Search Photos by Person

The `SYNO.Foto.Browse.Item` API with the `list` method supports filtering by `person_id`:

```python
# This works!
result = photos.session.request_data(
    api_name="SYNO.Foto.Browse.Item",
    api_path="entry.cgi",
    req_param={
        'method': 'list',
        'version': 1,
        'person_id': 88,  # Person ID
        'limit': 100,
        'offset': 0,
        'additional': json.dumps(['thumbnail', 'person'])
    }
)
```

**Example Output:**
```
cli.py download --person-id 88 --list --limit 5

=== Photos of Person 88 (Yuer Guo) ===
Found 5 photos:
  1. mmexport1771807937514.jpg (3.4 MB, ID: 90885)
  2. 20260208_160928.heic (1.7 MB, ID: 90813)
  3. 20260208_160927.heic (1.7 MB, ID: 90812)
  4. 20260208_160926.heic (1.7 MB, ID: 90814)
  5. 20260208_160925.heic (1.6 MB, ID: 90815)
```

## What Doesn't Work (Yet)

### Download API - SYNO.Foto.Download

The download endpoint exists but requires additional authentication parameters:

```
Endpoint: /photo/webapi/entry.cgi?api=SYNO.Foto.Download&method=download&version=1&id=<ID>&_sid=<SID>
Status: 403 Forbidden
```

**Possible Solutions:**
1. Different authentication header format needed
2. Additional parameters required (cache_key, unit_id format)
3. Session token handling differs from other endpoints
4. File Station API may be required instead

## API Endpoints Available

According to Synology Photos API documentation:

| Endpoint | Purpose | Status |
|----------|---------|--------|
| `SYNO.Foto.Browse.Item` list | Search items by person | ✅ Working |
| `SYNO.Foto.Download` | Download original file | ⚠️ 403 Error |
| `SYNO.Foto.Thumbnail` | Get thumbnail | Not tested |
| `SYNO.FotoTeam.Download` | Download from shared space | Not tested |

## How to Implement Full Support

### Option 1: Fix SYNO.Foto.Download Authentication
Need to determine:
- Correct authentication headers
- Required parameters for photo items
- Session handling differences

### Option 2: Use File Station API
Alternative approach using `SYNO.FileStation` to download files directly from the Photos folder storage location.

### Option 3: Use Browser Download URLs
Reverse-engineer how the web UI downloads photos and replicate that flow.

## Investigation Needed

1. **Capture browser requests** - Use DevTools to see how web UI downloads photos
2. **Check synology-api source** - See if there are hints about auth handling
3. **Test with curl** - Try different header combinations
4. **Look at related projects** - Check if other Synology API wrappers solved this

## References

- [Synology Photos API - Unofficial Documentation](https://github.com/zeichensatz/SynologyPhotosAPI)
- [py-synologydsm-api - Alternative Python wrapper](https://pypi.org/project/py-synologydsm-api/)
- [Synology Forum - Download discussions](https://community.synology.com/enu/forum/1/post/151693)

## Current Implementation

The `features/download.py` module provides:

```python
# List photos of a person - WORKS
items = download.get_person_photos(photos, person_id=88)

# Show photos - WORKS
download.list_person_photos(photos, person_id=88)

# Download photos - NOT YET IMPLEMENTED
# download.download_person_photos(photos, person_id=88)
```

## Usage

```bash
# List photos of person 88
python cli.py download --person-id 88 --list

# Get first 10 photos
python cli.py download --person-id 88 --list --limit 10

# Attempt download (currently shows available photos)
python cli.py download --person-id 88
```

## Next Steps

To complete the download feature:
1. Capture actual browser download requests
2. Identify missing authentication parameters
3. Test different authentication approaches
4. Implement successful download handler
5. Add progress bar and error handling
