"""User information feature."""


def get_user_info(photos):
    """Get and display user information."""
    user_info = photos.get_userinfo()

    if not user_info.get('success'):
        print("❌ Failed to get user info")
        return False

    data = user_info['data']
    print("\n=== User Info ===")
    print(f"User ID: {data['id']}")
    print(f"Name:    {data['name']}")

    if 'email' in data:
        print(f"Email:   {data['email']}")

    return True
