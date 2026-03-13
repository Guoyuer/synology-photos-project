"""Albums feature."""


def list_albums(photos, limit=None):
    """List all albums."""
    albums = photos.list_albums()

    if not albums.get('success'):
        print("❌ Failed to list albums")
        return False

    album_list = albums['data'].get('list', [])
    print(f"\n=== Albums ({len(album_list)}) ===")

    if not album_list:
        print("No albums found")
        return True

    display_count = limit if limit else len(album_list)
    for album in album_list[:display_count]:
        print(f"  - {album['name']} (ID: {album['id']})")

    if limit and len(album_list) > limit:
        print(f"  ... and {len(album_list) - limit} more")

    return True
