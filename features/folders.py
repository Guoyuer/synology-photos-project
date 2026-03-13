"""Folders feature."""


def list_folders(photos, limit=None):
    """List all folders."""
    folders = photos.list_folders(limit=100)

    if not folders.get('success'):
        print("❌ Failed to list folders")
        return False

    folder_list = folders['data'].get('list', [])
    total = folders['data'].get('list_total', len(folder_list))

    print(f"\n=== Folders ({total}) ===")

    if not folder_list:
        print("No folders found")
        return True

    display_count = limit if limit else len(folder_list)
    for folder in folder_list[:display_count]:
        parent_id = folder.get('parent', 'root')
        shared = "🔒 Shared" if folder.get('shared') else ""
        print(f"  - {folder['name']} (ID: {folder['id']}) {shared}".strip())

    if limit and len(folder_list) > limit:
        print(f"  ... and {len(folder_list) - limit} more")

    return True


def get_folder(photos, folder_id):
    """Get a specific folder's details."""
    try:
        folder = photos.get_folder(folder_id=folder_id)

        if not folder.get('success'):
            print(f"❌ Failed to get folder {folder_id}")
            return False

        # The API returns folder data in a 'folder' key
        data = folder.get('data', {}).get('folder', folder.get('folder'))

        if data:
            print(f"\n=== Folder Details (ID: {folder_id}) ===")
            print(f"Name:     {data.get('name', 'N/A')}")
            print(f"Parent:   {data.get('parent', 'root')}")
            print(f"Shared:   {'Yes' if data.get('shared') else 'No'}")
            print(f"Owner ID: {data.get('owner_user_id', 'N/A')}")
        else:
            print(f"❌ No folder data found")

        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
