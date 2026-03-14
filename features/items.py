"""Items feature."""


def list_items_in_folder(photos, folder_id, limit=None):
    """List items in a specific folder."""
    try:
        items = photos.list_item_in_folders(
            folder_id=folder_id,
            limit=limit or 100,
            additional=["person", "thumbnail"]
        )

        if not items.get('success'):
            print(f"❌ Failed to list items in folder {folder_id}")
            return False

        item_list = items['data'].get('list', [])
        total = len(item_list)

        print(f"\n=== Items in Folder {folder_id} ({total}) ===")

        if not item_list:
            print("No items found")
            return True

        for item in item_list:
            filename = item.get('filename', 'Unknown')
            item_type = item.get('item_type', 'unknown')
            time_str = ""
            if 'takentime' in item:
                time_str = f" [{item['takentime']}]"
            print(f"  - {filename} ({item_type}){time_str}")

        return True

    except Exception as e:
        print(f"❌ Error listing items: {e}")
        return False
