"""Unit tests for db_config.py."""

import os
from unittest.mock import patch

from db_config import get_db_params


class TestGetDbParams:
    def test_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            params = get_db_params()
        assert params["host"] == "192.168.1.169"
        assert params["port"] == 5432
        assert params["dbname"] == "synofoto"
        assert params["user"] == "postgres"

    def test_custom_env(self):
        env = {
            "NAS_DB_HOST": "10.0.0.1",
            "NAS_DB_PORT": "6543",
            "NAS_DB_NAME": "mydb",
            "NAS_DB_USER": "admin",
        }
        with patch.dict(os.environ, env, clear=True):
            params = get_db_params()
        assert params["host"] == "10.0.0.1"
        assert params["port"] == 6543
        assert params["dbname"] == "mydb"
        assert params["user"] == "admin"

    def test_returns_dict(self):
        params = get_db_params()
        assert isinstance(params, dict)
        assert set(params.keys()) == {"host", "port", "dbname", "user"}
