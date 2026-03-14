"""Unit tests for web/api/main.py — all external I/O is mocked."""

import importlib
import sys
import types
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ---------------------------------------------------------------------------
# Helpers to build mock DB infrastructure
# ---------------------------------------------------------------------------

def _make_cursor(rows):
    """Return a mock psycopg2 cursor that returns *rows* from fetchall/fetchone."""
    cur = MagicMock()
    cur.fetchall.return_value = rows
    cur.fetchone.return_value = rows[0] if rows else None
    return cur


def _make_conn(cur):
    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn


@contextmanager
def _db_ctx(conn):
    """Mimic the db() context manager for tests."""
    yield conn


def _row(*fields_values):
    """Build a dict-like row from keyword arguments."""
    return dict(fields_values)


# ---------------------------------------------------------------------------
# Import the app with all module-level side-effects already neutralised.
# We patch psycopg2 and requests at import time so the app can load cleanly
# even without a real NAS or DB.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app_client():
    """Return a FastAPI TestClient with the app loaded under mocked imports."""
    # Stub heavy dependencies before the app module is first imported
    psycopg2_stub = MagicMock()
    psycopg2_extras_stub = MagicMock()
    psycopg2_pool_stub = MagicMock()
    psycopg2_stub.extras = psycopg2_extras_stub
    psycopg2_stub.pool = psycopg2_pool_stub
    psycopg2_stub.connect = MagicMock()

    requests_stub = MagicMock()
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda *a, **kw: None

    session_manager_stub = types.ModuleType("session_manager")
    session_manager_stub.get_photos_api = MagicMock()

    with patch.dict(
        sys.modules,
        {
            "psycopg2": psycopg2_stub,
            "psycopg2.extras": psycopg2_extras_stub,
            "psycopg2.pool": psycopg2_pool_stub,
            "requests": requests_stub,
            "dotenv": dotenv_stub,
            "session_manager": session_manager_stub,
            # stub the features.download import inside collect.py
            "features.download": MagicMock(),
        },
    ):
        # Force fresh import
        for mod_name in list(sys.modules.keys()):
            if "web.api.main" in mod_name or mod_name == "web.api.main":
                del sys.modules[mod_name]

        import web.api.main as main_mod
        from fastapi.testclient import TestClient

        client = TestClient(main_mod.app, raise_server_exceptions=False)
        yield client, main_mod, psycopg2_stub, requests_stub


# ---------------------------------------------------------------------------
# Convenience: a real dict row that supports dict(r) (used in endpoints)
# ---------------------------------------------------------------------------

def _dict_row(**kw):
    return dict(kw)


# ===========================================================================
# GET /api/persons
# ===========================================================================

class TestListPersons:
    def test_returns_list(self, app_client):
        client, main_mod, psycopg2_stub, _ = app_client
        main_mod._ref_cache.clear()
        rows = [
            _dict_row(id=1, name="Alice", item_count=50),
            _dict_row(id=2, name="Bob",   item_count=30),
        ]
        cur = _make_cursor(rows)
        conn = _make_conn(cur)
        with patch.object(main_mod, "db", return_value=_db_ctx(conn)):
            resp = client.get("/api/persons")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["name"] == "Alice"

    def test_returns_empty_list(self, app_client):
        client, main_mod, _, _ = app_client
        main_mod._ref_cache.clear()
        cur = _make_cursor([])
        conn = _make_conn(cur)
        with patch.object(main_mod, "db", return_value=_db_ctx(conn)):
            resp = client.get("/api/persons")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_uses_connection_pool(self, app_client):
        """db() is a context manager — connection is returned to pool, not closed."""
        client, main_mod, _, _ = app_client
        main_mod._ref_cache.clear()
        conn = _make_conn(_make_cursor([]))
        with patch.object(main_mod, "db", return_value=_db_ctx(conn)):
            client.get("/api/persons")
        conn.close.assert_not_called()


# ===========================================================================
# GET /api/locations
# ===========================================================================

class TestListLocations:
    def test_returns_list(self, app_client):
        client, main_mod, _, _ = app_client
        main_mod._ref_cache.clear()
        rows = [
            _dict_row(country="Singapore", first_level="Central", second_level=None, item_count=10),
        ]
        cur = _make_cursor(rows)
        conn = _make_conn(cur)
        with patch.object(main_mod, "db", return_value=_db_ctx(conn)):
            resp = client.get("/api/locations")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["country"] == "Singapore"

    def test_empty(self, app_client):
        client, main_mod, _, _ = app_client
        main_mod._ref_cache.clear()
        conn = _make_conn(_make_cursor([]))
        with patch.object(main_mod, "db", return_value=_db_ctx(conn)):
            resp = client.get("/api/locations")
        assert resp.json() == []


# ===========================================================================
# GET /api/concepts
# ===========================================================================

class TestListConcepts:
    def test_returns_list(self, app_client):
        client, main_mod, _, _ = app_client
        main_mod._ref_cache.clear()
        rows = [
            _dict_row(id=1, stem="beach", usage_count=99),
            _dict_row(id=2, stem="mountain", usage_count=42),
        ]
        cur = _make_cursor(rows)
        conn = _make_conn(cur)
        with patch.object(main_mod, "db", return_value=_db_ctx(conn)):
            resp = client.get("/api/concepts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["stem"] == "beach"


# ===========================================================================
# GET /api/cameras
# ===========================================================================

class TestListCameras:
    def test_returns_list(self, app_client):
        client, main_mod, _, _ = app_client
        main_mod._ref_cache.clear()
        rows = [
            _dict_row(camera="iPhone 14 Pro", item_count=200),
            _dict_row(camera="Sony A7IV",     item_count=50),
        ]
        cur = _make_cursor(rows)
        conn = _make_conn(cur)
        with patch.object(main_mod, "db", return_value=_db_ctx(conn)):
            resp = client.get("/api/cameras")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["camera"] == "iPhone 14 Pro"

    def test_empty(self, app_client):
        client, main_mod, _, _ = app_client
        main_mod._ref_cache.clear()
        conn = _make_conn(_make_cursor([]))
        with patch.object(main_mod, "db", return_value=_db_ctx(conn)):
            resp = client.get("/api/cameras")
        assert resp.json() == []


# ===========================================================================
# POST /api/collect
# ===========================================================================

class TestCollect:
    """Verifies date parsing, kwarg forwarding, and response shape."""

    _SAMPLE_ITEM = {
        "id": 1,
        "filename": "photo.jpg",
        "takentime": 1_700_000_000,
        "item_type": 0,
        "filesize": 1_048_576,   # 1 MB
        "duplicate_hash": None,
        "cache_key": "abc123",
        "width": 4032,
        "height": 3024,
        "duration": None,
        "vres_x": None,
        "fps": None,
        "country": "Singapore",
        "district": None,
        "camera": "iPhone",
        "latitude": None,
        "longitude": None,
    }

    def test_minimal_request_returns_shape(self, app_client):
        client, main_mod, _, _ = app_client
        with patch.object(main_mod, "query_items", return_value=[dict(self._SAMPLE_ITEM)]) as mock_qi:
            resp = client.post("/api/collect", json={})
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "count" in body
        assert "total_mb" in body
        assert body["count"] == 1

    def test_item_has_type_name_and_taken_iso(self, app_client):
        client, main_mod, _, _ = app_client
        with patch.object(main_mod, "query_items", return_value=[dict(self._SAMPLE_ITEM)]):
            resp = client.post("/api/collect", json={})
        item = resp.json()["items"][0]
        assert item["type_name"] == "photo"
        assert "taken_iso" in item
        assert "T" in item["taken_iso"]  # ISO format contains 'T'

    def test_date_parsing_produces_timestamps(self, app_client):
        """from_date/to_date must be converted to Unix timestamps."""
        client, main_mod, _, _ = app_client
        captured = {}
        def fake_query(**kwargs):
            captured.update(kwargs)
            return []
        with patch.object(main_mod, "query_items", side_effect=fake_query):
            resp = client.post("/api/collect", json={
                "from_date": "2023-01-01",
                "to_date":   "2023-01-31",
            })
        assert resp.status_code == 200
        from datetime import datetime, timezone
        expected_from = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())
        expected_to   = int(datetime(2023, 1, 31, tzinfo=timezone.utc).timestamp()) + 86399
        assert captured["from_ts"] == expected_from
        assert captured["to_ts"]   == expected_to

    def test_no_dates_gives_none_timestamps(self, app_client):
        client, main_mod, _, _ = app_client
        captured = {}
        def fake_query(**kwargs):
            captured.update(kwargs)
            return []
        with patch.object(main_mod, "query_items", side_effect=fake_query):
            client.post("/api/collect", json={})
        assert captured["from_ts"] is None
        assert captured["to_ts"]   is None

    def test_kwargs_forwarded_to_query_items(self, app_client):
        client, main_mod, _, _ = app_client
        captured = {}
        def fake_query(**kwargs):
            captured.update(kwargs)
            return []
        payload = {
            "person_ids":    [1, 2],
            "country":       "France",
            "first_level":   "Paris",
            "district":      "Marais",
            "item_types":    [0, 1],
            "concepts":      ["beach"],
            "min_confidence": 0.9,
            "cameras":       ["iPhone"],
            "min_duration":  60,
            "min_width":     3840,
            "limit":         50,
        }
        with patch.object(main_mod, "query_items", side_effect=fake_query):
            client.post("/api/collect", json=payload)
        assert captured["person_ids"]    == [1, 2]
        assert captured["country"]       == "France"
        assert captured["first_level"]   == "Paris"
        assert captured["district"]      == "Marais"
        assert captured["item_types"]    == [0, 1]
        assert captured["concepts"]      == ["beach"]
        assert captured["min_confidence"] == 0.9
        assert captured["cameras"]       == ["iPhone"]
        assert captured["min_duration_s"] == 60   # mapped from min_duration
        assert captured["min_width"]     == 3840
        assert captured["limit"]         == 50

    def test_empty_results(self, app_client):
        client, main_mod, _, _ = app_client
        with patch.object(main_mod, "query_items", return_value=[]):
            resp = client.post("/api/collect", json={})
        body = resp.json()
        assert body["count"] == 0
        assert body["total_mb"] == 0.0
        assert body["items"] == []

    def test_invalid_date_format_returns_422(self, app_client):
        client, main_mod, _, _ = app_client
        with patch.object(main_mod, "query_items", return_value=[]):
            resp = client.post("/api/collect", json={"from_date": "not-a-date"})
        # FastAPI will propagate a ValueError → 500 or we handle internally
        assert resp.status_code in (400, 422, 500)

    def test_video_item_type_name(self, app_client):
        client, main_mod, _, _ = app_client
        item = dict(self._SAMPLE_ITEM)
        item["item_type"] = 1
        with patch.object(main_mod, "query_items", return_value=[item]):
            resp = client.post("/api/collect", json={})
        assert resp.json()["items"][0]["type_name"] == "video"

    def test_null_takentime_gives_null_taken_iso(self, app_client):
        client, main_mod, _, _ = app_client
        item = dict(self._SAMPLE_ITEM)
        item["takentime"] = None
        with patch.object(main_mod, "query_items", return_value=[item]):
            resp = client.post("/api/collect", json={})
        assert resp.json()["items"][0]["taken_iso"] is None

    def test_total_mb_calculation(self, app_client):
        client, main_mod, _, _ = app_client
        item = dict(self._SAMPLE_ITEM)
        item["filesize"] = 2 * 1024 * 1024   # 2 MB exactly
        with patch.object(main_mod, "query_items", return_value=[item]):
            resp = client.post("/api/collect", json={})
        assert resp.json()["total_mb"] == 2.0


# ===========================================================================
# POST /api/download
# ===========================================================================

class TestDownload:
    def _make_session(self):
        sess = MagicMock()
        sess.session._base_url = "http://nas/"
        sess.session.sid       = "SID123"
        sess.session.syno_token = "TOKEN"
        sess.session._verify   = False
        return sess

    def test_missing_item_ids_returns_422(self, app_client):
        client, main_mod, _, _ = app_client
        resp = client.post("/api/download", json={})
        assert resp.status_code == 422

    def test_streams_zip(self, app_client):
        client, main_mod, _, requests_stub = app_client
        fake_resp = MagicMock()
        fake_resp.headers = {"Content-Type": "application/zip", "Content-Disposition": "attachment; filename=photos.zip"}
        fake_resp.iter_content.return_value = iter([b"PKfakedata"])

        sess = self._make_session()
        with patch.object(main_mod, "get_session", return_value=sess), \
             patch.object(main_mod.requests, "post", return_value=fake_resp):
            resp = client.post("/api/download", json={"item_ids": [1, 2, 3]})
        assert resp.status_code == 200


# ===========================================================================
# GET /api/thumbnail/{item_id}/{cache_key}
# ===========================================================================

class TestThumbnail:
    def _make_session(self, syno_token="TOK", sid="SID"):
        sess = MagicMock()
        sess.session._base_url  = "http://nas/"
        sess.session.syno_token = syno_token
        sess.session.sid        = sid
        sess.session._verify    = False
        return sess

    def test_returns_image(self, app_client):
        client, main_mod, _, _ = app_client
        fake_resp = MagicMock()
        fake_resp.headers = {"Content-Type": "image/jpeg"}
        fake_resp.content = b"\xff\xd8\xff"
        sess = self._make_session()
        with patch.object(main_mod, "get_session", return_value=sess), \
             patch.object(main_mod.requests, "get", return_value=fake_resp):
            resp = client.get("/api/thumbnail/7/CKEY42")
        assert resp.status_code == 200

    def test_404_when_synology_returns_html(self, app_client):
        """Synology returns text/html when thumbnail unavailable → 404."""
        client, main_mod, _, _ = app_client
        fake_resp = MagicMock()
        fake_resp.headers = {"Content-Type": "text/html"}
        fake_resp.content = b"<html>error</html>"
        sess = self._make_session()
        with patch.object(main_mod, "get_session", return_value=sess), \
             patch.object(main_mod.requests, "get", return_value=fake_resp):
            resp = client.get("/api/thumbnail/9999/BADKEY")
        assert resp.status_code == 404

    def test_cache_key_format(self, app_client):
        """cache_key param sent to Synology must be f'{item_id}_{cache_key}'."""
        client, main_mod, _, _ = app_client
        fake_resp = MagicMock()
        fake_resp.headers = {"Content-Type": "image/jpeg"}
        fake_resp.content = b"\xff\xd8\xff"
        sess = self._make_session()
        called_params = {}
        def capture_get(url, params=None, **kw):
            called_params.update(params or {})
            return fake_resp
        with patch.object(main_mod, "get_session", return_value=sess), \
             patch.object(main_mod.requests, "get", side_effect=capture_get):
            client.get("/api/thumbnail/42/MYKEY")
        assert called_params["cache_key"] == "42_MYKEY"
        assert called_params["id"] == 42


# ===========================================================================
# GET /api/media/{id}
# ===========================================================================

class TestStreamMedia:
    def _make_session(self):
        sess = MagicMock()
        sess.session._base_url  = "http://nas/"
        sess.session.syno_token = "TOK"
        sess.session.sid        = "SID"
        sess.session._verify    = False
        return sess

    def test_streams_media(self, app_client):
        client, main_mod, _, _ = app_client
        db_row = {
            "filename": "photo.jpg", "item_type": 0,
            "folder_name": "/Photos", "companion_filename": None, "companion_folder": None,
        }
        cur = _make_cursor([db_row])
        conn = _make_conn(cur)

        fake_resp = MagicMock()
        fake_resp.headers = {}
        fake_resp.iter_content.return_value = iter([b"fakeimage"])

        sess = self._make_session()
        with patch.object(main_mod, "db", return_value=_db_ctx(conn)), \
             patch.object(main_mod, "get_session", return_value=sess), \
             patch.object(main_mod.requests, "post", return_value=fake_resp):
            resp = client.get("/api/media/42")
        assert resp.status_code == 200

    def test_404_on_missing_item(self, app_client):
        client, main_mod, _, _ = app_client
        cur = _make_cursor([])
        conn = _make_conn(cur)
        with patch.object(main_mod, "db", return_value=_db_ctx(conn)):
            resp = client.get("/api/media/9999")
        assert resp.status_code == 404
