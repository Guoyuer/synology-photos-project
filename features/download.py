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


def download_person_photos(photos, person_id, output_dir="downloads", limit=None, person_name=None, nas_ip=None, nas_port=None, nas_secure=False, nas_cert_verify=False):
    """
    Download all photos of a specific person.

    Args:
        photos: Photos API instance
        person_id: Person ID to download photos for
        output_dir: Directory to save photos
        limit: Max number of photos to download
        person_name: Person name for display
        nas_ip: NAS IP address
        nas_port: NAS port
        nas_secure: Use HTTPS
        nas_cert_verify: Verify SSL cert
    """
    name_str = f" ({person_name})" if person_name else ""
    print(f"\n=== Downloading Photos of Person {person_id}{name_str} ===")

    items = get_person_photos(photos, person_id, limit)

    if not items:
        print("No photos found to download")
        return False

    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)

    print(f"Downloading {len(items)} photos to {output_dir}/\n")

    # Get auth tokens from session
    syno_token = photos.session.syno_token
    sid = photos.session.sid

    success_count = 0
    failed_count = 0

    for i, item in enumerate(items, 1):
        filename = item.get('filename', 'Unknown')
        item_id = item.get('id')

        # Download the photo
        if download_item(
            item_id=item_id,
            filename=filename,
            output_dir=output_dir,
            syno_token=syno_token,
            sid=sid,
            nas_ip=nas_ip,
            nas_port=nas_port,
            nas_secure=nas_secure,
            nas_cert_verify=nas_cert_verify
        ):
            print(f"  ✅ {i}/{len(items)} {filename}")
            success_count += 1
        else:
            print(f"  ❌ {i}/{len(items)} {filename}")
            failed_count += 1

    print(f"\n✅ Downloaded: {success_count}")
    if failed_count > 0:
        print(f"❌ Failed: {failed_count}")

    return success_count > 0


def download_item(item_id, filename, output_dir, syno_token, sid, nas_ip, nas_port, nas_secure=False, nas_cert_verify=False):
    """Download a single original photo."""
    try:
        protocol = "https" if nas_secure else "http"
        url = f"{protocol}://{nas_ip}:{nas_port}/webapi/entry.cgi"

        # SynoToken in query string (CSRF token)
        params = {'SynoToken': syno_token}

        # Form data with _sid for authentication
        data = {
            'api': 'SYNO.Foto.Download',
            'method': 'download',
            'version': '2',
            'item_id': json.dumps([item_id]),
            'download_type': 'source',
            'force_download': 'true',
            '_sid': sid,
        }

        response = requests.post(
            url,
            params=params,
            data=data,
            verify=nas_cert_verify,
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


