"""Shared DB connection parameters — single source of truth."""

import os


def get_db_params() -> dict:
    """Return psycopg2 connection kwargs from environment variables."""
    return {
        "host": os.getenv("NAS_DB_HOST", "192.168.1.169"),
        "port": int(os.getenv("NAS_DB_PORT", "5432")),
        "dbname": os.getenv("NAS_DB_NAME", "synofoto"),
        "user": os.getenv("NAS_DB_USER", "postgres"),
    }
