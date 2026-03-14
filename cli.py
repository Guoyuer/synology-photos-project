#!/usr/bin/env python3
"""CLI tool for Synology Photos API."""

import os
import sys
import argparse
from dotenv import load_dotenv

from session_manager import get_photos_api, clear_session
from features import user, albums, folders, items, persons, download, collect

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


def get_photos_instance():
    """Get Photos API instance with session caching."""
    config = get_config()
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
    photos = get_photos_instance()
    user.get_user_info(photos)


def cmd_albums(args):
    """Handle albums command."""
    photos = get_photos_instance()
    albums.list_albums(photos, limit=args.limit)


def cmd_folders(args):
    """Handle folders command."""
    photos = get_photos_instance()

    if args.id:
        folders.get_folder(photos, args.id)
    else:
        folders.list_folders(photos, limit=args.limit)


def cmd_items(args):
    """Handle items command."""
    photos = get_photos_instance()
    items.list_items_in_folder(photos, args.folder, limit=args.limit)


def cmd_persons(args):
    """Handle persons command."""
    photos = get_photos_instance()

    # If person_id is provided, show photos for that person
    if args.person_id:
        if args.photos:
            download.list_person_photos(photos, args.person_id, limit=args.limit)
            if args.download:
                download.download_person_photos(photos, args.person_id, args.output, args.limit)
        else:
            print(f"Use --photos flag to list/download photos for person {args.person_id}")
    else:
        # List all persons
        persons.list_persons(photos, limit=args.limit)


def cmd_collect(args):
    """Handle collect command."""
    photos = get_photos_instance()
    has_audio = True if args.has_audio else (False if args.no_audio else None)
    has_gps   = True if args.has_gps   else (False if args.no_gps   else None)
    collect.collect(
        photos,
        persons=args.persons,
        location=args.location,
        from_date=args.from_date,
        to_date=args.to_date,
        item_types=args.type or [],
        output_dir=args.output,
        download=args.download,
        limit=args.limit,
        concepts=args.concepts or [],
        min_confidence=args.min_confidence,
        cameras=args.cameras or [],
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        min_width=args.min_width,
        min_fps=args.min_fps,
        video_codecs=args.codecs or [],
        has_audio=has_audio,
        has_gps=has_gps,
        sort_desc=args.sort_desc,
    )


def cmd_session(args):
    """Handle session command."""
    if args.action == 'clear':
        clear_session()
    elif args.action == 'status':
        from manage_session import show_status
        show_status()


def cmd_all(args):
    """Handle all command - show everything."""
    config = get_config()
    photos = get_photos_instance()

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
  %(prog)s persons --person-id 88 --photos --download   # Download photos
  %(prog)s session status                # Show session info
  %(prog)s session clear                 # Clear saved session
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

    # Collect command
    collect_parser = subparsers.add_parser('collect', help='Collect photos/videos by persons, location, and date')
    collect_parser.add_argument('--persons', nargs='+', metavar='NAME', help='Person names')
    collect_parser.add_argument('--location', type=str, help='Location name (country or region)')
    collect_parser.add_argument('--from', dest='from_date', metavar='YYYY-MM-DD', help='Start date (inclusive)')
    collect_parser.add_argument('--to', dest='to_date', metavar='YYYY-MM-DD', help='End date (inclusive)')
    collect_parser.add_argument('--type', nargs='+', choices=['photo', 'video', 'live', 'motion'], help='Media type(s)')
    collect_parser.add_argument('--output', type=str, help='Output directory (auto-named if omitted)')
    collect_parser.add_argument('--download', action='store_true', help='Download files (preview only without this)')
    collect_parser.add_argument('--limit', type=int, help='Cap number of items')
    collect_parser.add_argument('--concepts', nargs='+', metavar='STEM', help='AI concept stems (e.g. food beach)')
    collect_parser.add_argument('--min-confidence', type=float, default=0.7, metavar='0-1', help='Min concept confidence (default: 0.7)')
    collect_parser.add_argument('--cameras', nargs='+', metavar='MODEL', help='Camera model names')
    collect_parser.add_argument('--min-duration', type=int, metavar='SEC', help='Min video duration (seconds)')
    collect_parser.add_argument('--max-duration', type=int, metavar='SEC', help='Max video duration (seconds)')
    collect_parser.add_argument('--min-width', type=int, metavar='PX', help='Min video width in pixels (e.g. 3840 for 4K)')
    collect_parser.add_argument('--min-fps', type=int, metavar='FPS', help='Min frame rate (e.g. 60)')
    collect_parser.add_argument('--codecs', nargs='+', choices=['hevc', 'h264', 'vp9'], help='Video codec(s)')
    collect_parser.add_argument('--has-audio', action='store_true', help='Only items with audio')
    collect_parser.add_argument('--no-audio', action='store_true', help='Only items without audio')
    collect_parser.add_argument('--has-gps', action='store_true', help='Only items with GPS')
    collect_parser.add_argument('--no-gps', action='store_true', help='Only items without GPS')
    collect_parser.add_argument('--sort-desc', action='store_true', help='Sort newest first (default: oldest first)')

    # Session command
    session_parser = subparsers.add_parser('session', help='Manage login session')
    session_parser.add_argument('action', choices=['status', 'clear'], help='Session action')

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
        'collect': cmd_collect,
        'session': cmd_session,
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
