"""Session manager for persistent Synology Photos API login."""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from synology_api.photos import Photos


SESSION_FILE = Path.home() / '.synology_photos_session'
SESSION_EXPIRY_HOURS = 24  # Sessions expire after 24 hours of no use


def save_session(photos_obj, is_new=True):
    """Save session credentials to file."""
    now = datetime.now().isoformat()

    # Load existing session to preserve creation time
    existing_data = None
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, 'r') as f:
                existing_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    # Use existing created_at if available, otherwise set to now
    created_at = now
    if existing_data and existing_data.get('created_at'):
        created_at = existing_data['created_at']

    session_data = {
        'sid': photos_obj.session.sid,
        'syno_token': photos_obj.session.syno_token,
        'created_at': created_at,
        'last_used': now,
    }

    with open(SESSION_FILE, 'w') as f:
        json.dump(session_data, f)

    if is_new:
        print(f"Session saved to {SESSION_FILE}")


def load_session_from_file():
    """Load session credentials from file."""
    if not SESSION_FILE.exists():
        return None

    try:
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def is_session_expired(session_data):
    """Check if session has expired."""
    if not session_data or 'last_used' not in session_data:
        return True

    last_used = datetime.fromisoformat(session_data['last_used'])
    expiry_time = last_used + timedelta(hours=SESSION_EXPIRY_HOURS)
    return datetime.now() > expiry_time


def get_photos_api(nas_ip, nas_port, nas_username, nas_password,
                   nas_secure=False, nas_cert_verify=False,
                   nas_dsm_version=7, nas_otp=None, use_cache=True):
    """
    Get Photos API instance with session caching.

    Args:
        use_cache: If True, try to load cached session first

    Returns:
        Photos object and whether it's using cached session
    """
    cached_session = None

    if use_cache:
        cached_session = load_session_from_file()

    # Create Photos object
    photos = Photos(
        ip_address=nas_ip,
        port=nas_port,
        username=nas_username,
        password=nas_password,
        secure=nas_secure,
        cert_verify=nas_cert_verify,
        dsm_version=nas_dsm_version,
        debug=True,
        otp_code=nas_otp
    )

    # Try to use cached session if not expired
    if cached_session and not is_session_expired(cached_session):
        try:
            photos.session._sid = cached_session['sid']
            photos.session._syno_token = cached_session['syno_token']

            # Verify session is still valid by making a test call
            user_info = photos.get_userinfo()
            if user_info.get('success'):
                print(f"Using cached session (logged in as {user_info['data']['name']})")
                # Update last_used timestamp
                save_session(photos, is_new=False)
                return photos, True  # Return True for cached
        except Exception as e:
            print(f"Cached session invalid: {e}")
            # Fall through to login again

    # Session doesn't exist, is expired, or is invalid, login fresh
    print("Logging in with credentials...")
    # Photos object already logged in during __init__
    save_session(photos, is_new=True)
    return photos, False  # Return False for fresh login


def clear_session():
    """Clear saved session file."""
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
        print(f"Session cleared from {SESSION_FILE}")
