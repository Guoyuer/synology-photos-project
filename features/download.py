"""Download feature for photos by person."""

import json
from pathlib import Path
import requests


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


def list_person_photos(photos, person_id, limit=None):
    """List all photos containing a specific person."""
    print(f"\n=== Photos of Person {person_id} ===")

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


def download_person_photos(photos, person_id, output_dir="downloads", limit=None):
    """
    Download all photos of a specific person.

    Args:
        photos: Photos API instance
        person_id: Person ID to download photos for
        output_dir: Directory to save photos
        limit: Max number of photos to download
    """
    print(f"\n=== Downloading Photos of Person {person_id} ===")

    items = get_person_photos(photos, person_id, limit)

    if not items:
        print("No photos found to download")
        return False

    Path(output_dir).mkdir(exist_ok=True)
    print(f"Downloading {len(items)} photos to {output_dir}/\n")

    success_count = 0
    failed_count = 0

    for i, item in enumerate(items, 1):
        filename = item.get('filename', 'Unknown')
        item_id = item.get('id')

        if download_item(photos, item_id, filename, output_dir):
            print(f"  ✅ {i}/{len(items)} {filename}")
            success_count += 1
        else:
            print(f"  ❌ {i}/{len(items)} {filename}")
            failed_count += 1

    print(f"\n✅ Downloaded: {success_count}")
    if failed_count > 0:
        print(f"❌ Failed: {failed_count}")

    return success_count > 0


def download_item(photos, item_id, filename, output_dir):
    """Download a single original photo."""
    try:
        url = photos.session._base_url + 'entry.cgi'

        params = {'SynoToken': photos.session.syno_token}
        data = {
            'api': 'SYNO.Foto.Download',
            'method': 'download',
            'version': '2',
            'item_id': json.dumps([item_id]),
            'download_type': 'source',
            'force_download': 'true',
            '_sid': photos.session.sid,
        }

        response = requests.post(
            url,
            params=params,
            data=data,
            verify=photos.session._verify,
            stream=True,
            timeout=60,
        )

        content_type = response.headers.get('Content-Type', '')
        if response.status_code == 200 and 'json' not in content_type:
            output_path = Path(output_dir) / filename
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True

        return False

    except Exception:
        return False


