#!/usr/bin/env python3
"""CLI tool for Synology Photos API."""

import os
import sys
import argparse
from dotenv import load_dotenv

from session_manager import get_photos_api
from features import user, albums, folders, items, persons, download

# Load environment variables
load_dotenv()


def get_config():
    """Get configuration from environment."""
    return {
        'nas_ip': os.getenv('NAS_IP'),
        'nas_port': os.getenv('NAS_PORT'),
        'nas_username': os.getenv('NAS_USERNAME'),
        'nas_password': os.getenv('NAS_PASSWORD'),
        'nas_secure': os.getenv('NAS_SECURE', 'False').lower() == 'true',
        'nas_cert_verify': os.getenv('NAS_CERT_VERIFY', 'False').lower() == 'true',
        'nas_dsm_version': int(os.getenv('NAS_DSM_VERSION', '7')),
        'nas_otp': os.getenv('NAS_OTP_CODE') or None,
    }


def get_photos_instance(config):
    """Get Photos API instance with session caching."""
    try:
        photos, cached = get_photos_api(
            nas_ip=config['nas_ip'],
            nas_port=config['nas_port'],
            nas_username=config['nas_username'],
            nas_password=config['nas_password'],
            nas_secure=config['nas_secure'],
            nas_cert_verify=config['nas_cert_verify'],
            nas_dsm_version=config['nas_dsm_version'],
            nas_otp=config['nas_otp'],
            use_cache=True
        )
        return photos
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)


# Command handlers
def cmd_user(args):
    """Handle user command."""
    config = get_config()
    photos = get_photos_instance(config)
    user.get_user_info(photos)


def cmd_albums(args):
    """Handle albums command."""
    config = get_config()
    photos = get_photos_instance(config)
    albums.list_albums(photos, limit=args.limit)


def cmd_folders(args):
    """Handle folders command."""
    config = get_config()
    photos = get_photos_instance(config)

    if args.id:
        folders.get_folder(photos, args.id)
    else:
        folders.list_folders(photos, limit=args.limit)


def cmd_items(args):
    """Handle items command."""
    if not args.folder:
        print("❌ Error: --folder is required")
        sys.exit(1)

    config = get_config()
    photos = get_photos_instance(config)
    items.list_items_in_folder(photos, args.folder, limit=args.limit)


def cmd_persons(args):
    """Handle persons command."""
    config = get_config()
    photos = get_photos_instance(config)

    # If person_id is provided, show photos for that person
    if args.person_id:
        if args.photos:
            download.list_person_photos(photos, args.person_id, None, limit=args.limit)
            if args.download:
                download.download_person_photos(
                    photos,
                    args.person_id,
                    args.output,
                    args.limit,
                    None,
                    nas_ip=config['nas_ip'],
                    nas_port=config['nas_port'],
                    nas_secure=config['nas_secure'],
                    nas_cert_verify=config['nas_cert_verify']
                )
        else:
            print(f"Use --photos flag to list/download photos for person {args.person_id}")
    else:
        # List all persons
        persons.list_persons(photos, limit=args.limit)


def cmd_all(args):
    """Handle all command - show everything."""
    config = get_config()
    photos = get_photos_instance(config)

    print(f"\nConnected to {config['nas_ip']}:{config['nas_port']}")

    user.get_user_info(photos)
    albums.list_albums(photos, limit=5)
    folders.list_folders(photos, limit=5)
    persons.list_persons(photos, limit=10)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Synology Photos API CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s user                          # Get user info
  %(prog)s albums                        # List all albums
  %(prog)s albums --limit 10             # List first 10 albums
  %(prog)s folders                       # List all folders
  %(prog)s folders --id 3                # Get details for folder ID 3
  %(prog)s items --folder 166            # List items in folder ID 166
  %(prog)s items --folder 166 --limit 20 # List 20 items
  %(prog)s persons                       # List all persons
  %(prog)s persons --limit 20            # List first 20 persons
  %(prog)s persons --person-id 88 --photos        # List photos of person 88
  %(prog)s persons --person-id 88 --photos --limit 10   # List 10 photos
  %(prog)s persons --person-id 88 --photos --download   # Download (when ready)
  %(prog)s all                           # Show everything
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # User command
    subparsers.add_parser('user', help='Get user information')

    # Albums command
    albums_parser = subparsers.add_parser('albums', help='List albums')
    albums_parser.add_argument('--limit', type=int, help='Limit number of results')

    # Folders command
    folders_parser = subparsers.add_parser('folders', help='List folders')
    folders_parser.add_argument('--id', type=int, help='Get details for a specific folder ID')
    folders_parser.add_argument('--limit', type=int, help='Limit number of results')

    # Items command
    items_parser = subparsers.add_parser('items', help='List items in a folder')
    items_parser.add_argument('--folder', type=int, required=True, help='Folder ID')
    items_parser.add_argument('--limit', type=int, help='Limit number of results')

    # Persons command
    persons_parser = subparsers.add_parser('persons', help='List persons or manage photos of a person')
    persons_parser.add_argument('--limit', type=int, help='Limit number of results')
    persons_parser.add_argument('--person-id', type=int, help='Person ID to show photos for')
    persons_parser.add_argument('--photos', action='store_true', help='Show photos for --person-id')
    persons_parser.add_argument('--download', action='store_true', help='Download photos (requires --photos)')
    persons_parser.add_argument('--output', type=str, default='downloads', help='Output directory for downloads')

    # All command
    subparsers.add_parser('all', help='Show all information')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to command handler
    commands = {
        'user': cmd_user,
        'albums': cmd_albums,
        'folders': cmd_folders,
        'items': cmd_items,
        'persons': cmd_persons,
        'all': cmd_all,
    }

    handler = commands.get(args.command)
    if handler:
        try:
            handler(args)
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            sys.exit(0)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
