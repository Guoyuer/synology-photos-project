"""Persons feature."""

import json


def list_persons(photos, limit=None):
    """List all persons (people) with photo counts."""
    try:
        persons = photos.session.request_data(
            api_name="SYNO.Foto.Browse.Person",
            api_path="entry.cgi",
            req_param={
                "method": "list",
                "version": 1,
                "additional": json.dumps(["thumbnail"]),
                "offset": 0,
                "limit": 1000,
                "show_more": False,
                "show_hidden": False
            }
        )

        if not persons.get('success'):
            print("❌ Failed to list persons")
            return False

        person_list = persons['data'].get('list', [])
        total = len(person_list)

        print(f"\n=== Persons ({total}) ===")

        if not person_list:
            print("No persons found")
            return True

        display_count = limit if limit else len(person_list)
        for person in person_list[:display_count]:
            name = person.get('name', '(Unknown)')
            person_id = person.get('id', 'N/A')
            item_count = person.get('item_count', 0)
            print(f"  - {name} (ID: {person_id}, Photos: {item_count})")

        if limit and len(person_list) > limit:
            print(f"  ... and {len(person_list) - limit} more")

        return True

    except Exception as e:
        print(f"❌ Error listing persons: {e}")
        return False
