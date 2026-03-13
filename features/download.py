"""Download feature for photos by person."""

import json
import os
from pathlib import Path


def get_person_photos(photos, person_id, limit=None):
    """Get all photos containing a specific person.

    Args:
        photos: Photos API instance
        person_id: ID of the person to search for
        limit: Maximum number of photos to return

    Returns:
        List of photo items or empty list if none found
    """
    try:
        result = photos.session.request_data(
            api_name="SYNO.Foto.Browse.Item",
            api_path="entry.cgi",
            req_param={
                'method': 'list',
                'version': 1,
                'person_id': person_id,
                'limit': limit or 1000,
                'offset': 0,
                'additional': json.dumps(['thumbnail', 'person'])
            }
        )

        if result.get('success'):
            return result.get('data', {}).get('list', [])
        else:
            return []

    except Exception as e:
        print(f"❌ Error fetching photos: {e}")
        return []


def list_person_photos(photos, person_id, person_name=None, limit=None):
    """List all photos containing a specific person."""
    name_str = f" ({person_name})" if person_name else ""
    print(f"\n=== Photos of Person {person_id}{name_str} ===")

    items = get_person_photos(photos, person_id, limit)

    if not items:
        print("No photos found")
        return True

    print(f"Found {len(items)} photos:")
    for i, item in enumerate(items, 1):
        filename = item.get('filename', 'Unknown')
        size_mb = item.get('filesize', 0) / (1024 * 1024)
        print(f"  {i}. {filename} ({size_mb:.1f} MB, ID: {item['id']})")

    return True


def download_person_photos(photos, person_id, output_dir="downloads", limit=None, person_name=None):
    """
    Download all photos of a specific person.

    NOTE: Direct download via SYNO.Foto.Download API requires additional authentication
    or parameters not yet documented in synology-api library.

    This is a placeholder for future implementation.
    See: https://github.com/zeichensatz/SynologyPhotosAPI
    """
    name_str = f" ({person_name})" if person_name else ""
    print(f"\n=== Downloading Photos of Person {person_id}{name_str} ===")

    items = get_person_photos(photos, person_id, limit)

    if not items:
        print("No photos found to download")
        return False

    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)

    print(f"\n⚠️  Download feature requires additional implementation:")
    print(f"   - {len(items)} photos available for download")
    print(f"   - API endpoint: SYNO.Foto.Download")
    print(f"   - Status: Requires authentication headers/parameters not yet supported")
    print(f"\nPhotos ready for download:")

    for i, item in enumerate(items, 1):
        filename = item.get('filename', 'Unknown')
        item_id = item.get('id', 'N/A')
        print(f"  {i}. {filename} (ID: {item_id})")

    return False


def get_download_url(nas_ip, nas_port, item_id, cache_key=None, nas_secure=False):
    """
    Generate a download URL for a photo.

    WARNING: Direct URLs may require authentication headers.
    Use with session management.
    """
    protocol = "https" if nas_secure else "http"
    base_url = f"{protocol}://{nas_ip}:{nas_port}/photo/webapi/entry.cgi"

    if cache_key:
        url = f"{base_url}?api=SYNO.Foto.Download&method=download&version=1&cache_key={cache_key}&unit_id={item_id}"
    else:
        url = f"{base_url}?api=SYNO.Foto.Download&method=download&version=1&id={item_id}"

    return url
