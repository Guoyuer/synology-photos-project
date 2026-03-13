#!/usr/bin/env python3
"""Example script to interact with Synology Photos API."""

import os
from dotenv import load_dotenv
from synology_api.photos import Photos

# Load environment variables
load_dotenv()

def main():
    # Get configuration from environment
    nas_ip = os.getenv('NAS_IP')
    nas_port = os.getenv('NAS_PORT')
    nas_username = os.getenv('NAS_USERNAME')
    nas_password = os.getenv('NAS_PASSWORD')
    nas_secure = os.getenv('NAS_SECURE', 'False').lower() == 'true'
    nas_cert_verify = os.getenv('NAS_CERT_VERIFY', 'False').lower() == 'true'
    nas_dsm_version = int(os.getenv('NAS_DSM_VERSION', '7'))
    nas_otp = os.getenv('NAS_OTP_CODE') or None

    print(f"Connecting to {nas_ip}:{nas_port}...")

    # Initialize Photos API
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

    # Get user info
    print("\n=== User Info ===")
    user_info = photos.get_userinfo()
    print(f"Success: {user_info.get('success')}")
    if user_info.get('success'):
        print(f"User ID: {user_info['data']['id']}")
        print(f"Name: {user_info['data']['name']}")

    # List albums
    print("\n=== Albums ===")
    albums = photos.list_albums()
    if albums.get('success'):
        print(f"Total albums: {len(albums['data']['list'])}")
        for album in albums['data']['list'][:5]:  # Show first 5
            print(f"  - {album['name']} (ID: {album['id']})")

    # List folders
    print("\n=== Folders ===")
    folders = photos.list_folders(limit=10)
    if folders.get('success'):
        print(f"Total folders: {folders['data']['list_total']}")
        for folder in folders['data']['list'][:5]:  # Show first 5
            print(f"  - {folder['name']} (ID: {folder['id']})")

    # List items
    print("\n=== Items in root folder ===")
    items = photos.list_item_in_folders(
        folder_id=0,
        limit=10,
        additional=["person", "thumbnail"]
    )
    if items.get('success'):
        print(f"Total items: {items['data']['list_total']}")
        for item in items['data']['list'][:5]:  # Show first 5
            print(f"  - {item['filename']} (Type: {item['item_type']})")

if __name__ == '__main__':
    main()
