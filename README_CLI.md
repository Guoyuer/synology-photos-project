# Synology Photos API CLI

A modular command-line interface for the Synology Photos API with persistent session management.

## Quick Start

```bash
# Show help
python cli.py --help

# Get user info
python cli.py user

# List all persons
python cli.py persons

# List first 10 folders
python cli.py folders --limit 10

# List items in a folder
python cli.py items --folder 166 --limit 20

# Show everything
python cli.py all
```

## Commands

### `cli.py user`
Get current user information (ID, name, email).

```bash
python cli.py user
```

### `cli.py albums [--limit N]`
List all albums with optional limit.

```bash
python cli.py albums                # List all albums
python cli.py albums --limit 10     # List first 10 albums
```

### `cli.py folders [--id ID] [--limit N]`
List all folders or get details for a specific folder.

```bash
python cli.py folders                       # List all folders
python cli.py folders --limit 5             # List first 5 folders
python cli.py folders --id 166              # Get details for folder ID 166
```

### `cli.py items --folder ID [--limit N]`
List items (photos/videos) in a specific folder.

```bash
python cli.py items --folder 166            # List all items in folder 166
python cli.py items --folder 166 --limit 20 # List 20 items
```

### `cli.py persons [--person-id ID] [--photos] [--limit N] [--download] [--output DIR]`
List all persons or show photos of a specific person.

```bash
python cli.py persons                            # List all persons
python cli.py persons --limit 20                 # List first 20 persons
python cli.py persons --person-id 88 --photos    # List photos of person 88
python cli.py persons --person-id 88 --photos --limit 10   # List 10 photos
python cli.py persons --person-id 88 --photos --download   # Download (when available)
python cli.py persons --person-id 88 --photos --output ./my_photos  # Custom output dir
```

**Status:**
- ✅ List persons: Works
- ✅ List photos by person: Works
- ⚠️ Download photos: Requires API authentication fix (see DOWNLOAD_FEATURE.md)

### `cli.py all`
Show comprehensive overview (user, albums, folders, persons).

```bash
python cli.py all
```

## Session Management

The CLI automatically uses persistent sessions. Sessions are cached in `~/.synology_photos_session`.

### View session status
```bash
python manage_session.py status
```

Output shows:
- Created time
- Last used time
- Expiry time (24 hours of inactivity)
- Session validity status

### Clear session
```bash
python manage_session.py clear
```

The next command will create a fresh login.

## Configuration

Set environment variables in `.env`:

```env
NAS_IP=192.168.1.169
NAS_PORT=5000
NAS_USERNAME=your_username
NAS_PASSWORD=your_password
NAS_SECURE=False
NAS_CERT_VERIFY=False
NAS_DSM_VERSION=7
NAS_OTP_CODE=optional_2fa_code
```

## Architecture

```
cli.py                          # Main CLI entry point
├── session_manager.py          # Session caching & authentication
├── manage_session.py           # Session management utility
└── features/                   # Feature modules
    ├── user.py                 # User information
    ├── albums.py               # Album operations
    ├── folders.py              # Folder operations
    ├── items.py                # Item/photo operations
    └── persons.py              # Person/face detection
```

## Examples

### Backup persons to file
```bash
python cli.py persons | grep -E '^\s+-' > persons_backup.txt
```

### Check folder structure
```bash
python cli.py folders --limit 100
```

### Find items in specific folder
```bash
python cli.py items --folder 3 --limit 50
```

### Monitor session
```bash
watch -n 5 "python manage_session.py status"
```

## Tips

- Commands are modular - easily add new features
- Sessions auto-refresh on each use (24-hour inactivity timeout)
- Failed sessions auto-refresh with fresh login
- All commands use color output for clarity
- Use `--help` on any command for more info

```bash
python cli.py folders --help
python cli.py items --help
```
