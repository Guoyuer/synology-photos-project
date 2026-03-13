#!/usr/bin/env python3
"""Utility to manage Synology Photos API session."""

import sys
from datetime import datetime, timedelta
from session_manager import (
    clear_session, load_session_from_file, SESSION_FILE,
    is_session_expired, SESSION_EXPIRY_HOURS
)


def format_time_ago(iso_string):
    """Convert ISO datetime string to 'X time ago' format."""
    dt = datetime.fromisoformat(iso_string)
    now = datetime.now()
    diff = now - dt

    if diff.total_seconds() < 60:
        return "just now"
    elif diff.total_seconds() < 3600:
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes}m ago"
    elif diff.total_seconds() < 86400:
        hours = int(diff.total_seconds() / 3600)
        return f"{hours}h ago"
    else:
        days = int(diff.total_seconds() / 86400)
        return f"{days}d ago"


def show_status():
    """Show detailed session status."""
    session = load_session_from_file()
    if not session:
        print("❌ No saved session found")
        return

    print(f"📁 Session file: {SESSION_FILE}")
    print()

    # Created time (with fallback for old sessions)
    if 'created_at' in session:
        created = datetime.fromisoformat(session['created_at'])
        print(f"✅ Created:     {created.strftime('%Y-%m-%d %H:%M:%S')} ({format_time_ago(session['created_at'])})")
    else:
        print(f"✅ Created:     Unknown (legacy session)")

    # Last used time (with fallback for old sessions)
    if 'last_used' in session:
        last_used = datetime.fromisoformat(session['last_used'])
        print(f"🕐 Last used:   {last_used.strftime('%Y-%m-%d %H:%M:%S')} ({format_time_ago(session['last_used'])})")

        # Expiry time
        expiry = last_used + timedelta(hours=SESSION_EXPIRY_HOURS)
        time_remaining = (expiry - datetime.now()).total_seconds()

        if time_remaining > 0:
            hours_left = int(time_remaining / 3600)
            mins_left = int((time_remaining % 3600) / 60)
            print(f"⏰ Expires in:   {hours_left}h {mins_left}m")
            print(f"   Expiry time: {expiry.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"⚠️  Expired:     {expiry.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"🕐 Last used:   Unknown (legacy session)")

    # Status
    is_expired = is_session_expired(session)
    status = "🔴 EXPIRED (needs refresh)" if is_expired else "🟢 VALID"
    print()
    print(f"Status: {status}")

    # Session tokens (masked)
    print()
    print(f"Session ID: {session['sid'][:20]}...")
    print(f"Syno Token: {session['syno_token']}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python manage_session.py [clear|status]")
        print("\nCommands:")
        print("  clear   - Clear the saved session")
        print("  status  - Show current session status")
        return

    command = sys.argv[1].lower()

    if command == 'clear':
        clear_session()
    elif command == 'status':
        show_status()
    else:
        print(f"Unknown command: {command}")


if __name__ == '__main__':
    main()
