"""Unit tests for features/collect.py — psycopg2 is fully mocked."""

import sys
import types
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Patch psycopg2 at module level so features.collect can import cleanly.
# We also stub features.download which collect.py imports.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True, scope="module")
def _stub_heavy_imports():
    """Install lightweight stubs for psycopg2 and features.download."""
    psycopg2_stub = MagicMock()
    psycopg2_stub.connect = MagicMock()

    download_stub = types.ModuleType("features.download")
    download_stub.download_item = MagicMock()

    with patch.dict(
        sys.modules,
        {
            "psycopg2": psycopg2_stub,
            "features.download": download_stub,
        },
    ):
        # Remove any previously cached version of the module
        for key in list(sys.modules.keys()):
            if key in ("features.collect",):
                del sys.modules[key]
        yield psycopg2_stub


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db(rows, description=None):
    """
    Return (conn_mock, cur_mock, psycopg2_stub_configured).
    *rows* is a list of tuples (matching *description* column order).
    *description* defaults to the standard query_items column set.
    """
    if description is None:
        description = [
            ("id",), ("filename",), ("takentime",), ("item_type",),
            ("filesize",), ("duplicate_hash",), ("cache_key",),
            ("width",), ("height",), ("duration",), ("vres_x",),
            ("fps",), ("country",), ("district",), ("camera",),
            ("latitude",), ("longitude",),
        ]

    cur = MagicMock()
    cur.description = description
    cur.fetchall.return_value = rows
    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


def _row_tuple(**kw):
    """Build a tuple from keyword args in a fixed column order."""
    cols = [
        "id", "filename", "takentime", "item_type",
        "filesize", "duplicate_hash", "cache_key",
        "width", "height", "duration", "vres_x",
        "fps", "country", "district", "camera",
        "latitude", "longitude",
    ]
    return tuple(kw.get(c) for c in cols)


def _default_row(**overrides):
    defaults = {
        "id": 1, "filename": "img.jpg", "takentime": 1_700_000_000,
        "item_type": 0, "filesize": 1024, "duplicate_hash": None,
        "cache_key": "ck", "width": 1920, "height": 1080,
        "duration": None, "vres_x": None, "fps": None,
        "country": "SG", "district": None, "camera": "iPhone",
        "latitude": None, "longitude": None,
    }
    defaults.update(overrides)
    return _row_tuple(**defaults)


# ---------------------------------------------------------------------------
# Import the module under test (after stubs are in place)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def collect_mod(_stub_heavy_imports):
    import importlib
    import features.collect as mod
    return mod


@pytest.fixture()
def psycopg2_mock(_stub_heavy_imports):
    return _stub_heavy_imports


# ===========================================================================
# query_items — SQL generation
# ===========================================================================

class TestQueryItemsSQL:
    """Each test verifies which clauses appear (or don't) in the SQL string."""

    def _run(self, collect_mod, psycopg2_mock, rows=None, **kwargs):
        """Run query_items with given kwargs, return (sql_str, params, result_rows)."""
        if rows is None:
            rows = [_default_row()]
        conn, cur = _make_db(rows)
        psycopg2_mock.connect.return_value = conn
        result = collect_mod.query_items(**kwargs)
        sql_called, params_called = cur.execute.call_args[0]
        return sql_called, params_called, result

    # -- No filters ----------------------------------------------------------

    def test_no_filters_no_extra_conditions(self, collect_mod, psycopg2_mock):
        sql, params, _ = self._run(collect_mod, psycopg2_mock)
        # Only the base 1=1 condition; no person/location/date extras
        assert "1=1" in sql
        assert "EXISTS" not in sql or "concept" not in sql   # no concept filter
        assert "many_unit_has_many_person" not in sql
        assert "LIMIT %s" not in sql

    # -- Person filters ------------------------------------------------------

    def test_person_ids_single_uses_exists(self, collect_mod, psycopg2_mock):
        sql, params, _ = self._run(collect_mod, psycopg2_mock, person_ids=[1])
        assert "EXISTS" in sql
        assert "many_unit_has_many_person" in sql
        assert 1 in params

    def test_person_ids_multiple_uses_joins(self, collect_mod, psycopg2_mock):
        sql, params, _ = self._run(collect_mod, psycopg2_mock, person_ids=[1, 2])
        # Should have one JOIN per person (intersection)
        assert sql.count("JOIN many_unit_has_many_person") == 2
        assert 1 in params
        assert 2 in params

    # -- Location filters ----------------------------------------------------

    def test_country_condition(self, collect_mod, psycopg2_mock):
        sql, params, _ = self._run(collect_mod, psycopg2_mock, country="Singapore")
        assert "gi2.country = %s" in sql
        assert "Singapore" in params

    def test_country_and_first_level(self, collect_mod, psycopg2_mock):
        sql, params, _ = self._run(collect_mod, psycopg2_mock, country="France", first_level="Paris")
        assert "gi2.country = %s" in sql
        assert "gi2.first_level = %s" in sql
        assert "France" in params
        assert "Paris" in params

    def test_country_and_district(self, collect_mod, psycopg2_mock):
        sql, params, _ = self._run(collect_mod, psycopg2_mock, country="France", district="Marais")
        assert "gi2.country = %s" in sql
        assert "gi2.second_level = %s" in sql
        assert "France" in params
        assert "Marais" in params

    # -- Date range ----------------------------------------------------------

    def test_from_ts_condition(self, collect_mod, psycopg2_mock):
        sql, params, _ = self._run(collect_mod, psycopg2_mock, from_ts=1000)
        assert "u.takentime >= %s" in sql
        assert 1000 in params

    def test_to_ts_condition(self, collect_mod, psycopg2_mock):
        sql, params, _ = self._run(collect_mod, psycopg2_mock, to_ts=2000)
        assert "u.takentime <= %s" in sql
        assert 2000 in params

    def test_date_range_both(self, collect_mod, psycopg2_mock):
        sql, params, _ = self._run(collect_mod, psycopg2_mock, from_ts=1000, to_ts=2000)
        assert "u.takentime >= %s" in sql
        assert "u.takentime <= %s" in sql
        assert 1000 in params
        assert 2000 in params

    # -- Item type -----------------------------------------------------------

    def test_item_types_condition(self, collect_mod, psycopg2_mock):
        sql, params, _ = self._run(collect_mod, psycopg2_mock, item_types=[0, 1])
        assert "u.item_type = ANY(%s)" in sql
        assert [0, 1] in params

    # -- Concepts ------------------------------------------------------------

    def test_concepts_condition(self, collect_mod, psycopg2_mock):
        sql, params, _ = self._run(collect_mod, psycopg2_mock, concepts=["beach"], min_confidence=0.8)
        assert "many_unit_has_many_concept" in sql
        assert "c.stem = ANY(%s)" in sql
        assert "mc.confidence >= %s" in sql
        assert ["beach"] in params
        assert 0.8 in params

    # -- Cameras -------------------------------------------------------------

    def test_cameras_condition(self, collect_mod, psycopg2_mock):
        sql, params, _ = self._run(collect_mod, psycopg2_mock, cameras=["iPhone"])
        assert "m.camera = ANY(%s)" in sql
        assert ["iPhone"] in params

    # -- Video filters -------------------------------------------------------

    def test_min_duration_converts_to_ms(self, collect_mod, psycopg2_mock):
        sql, params, _ = self._run(collect_mod, psycopg2_mock, min_duration_s=30)
        assert "va2.duration >= %s" in sql
        assert 30_000 in params   # 30 seconds * 1000

    def test_min_width_condition(self, collect_mod, psycopg2_mock):
        sql, params, _ = self._run(collect_mod, psycopg2_mock, min_width=3840)
        assert "va3" in sql
        assert "resolution_x" in sql
        assert 3840 in params

    # -- LIMIT ---------------------------------------------------------------

    def test_limit_appended(self, collect_mod, psycopg2_mock):
        sql, params, _ = self._run(collect_mod, psycopg2_mock, limit=10)
        assert "LIMIT %s" in sql
        assert 10 in params

    def test_no_limit_when_not_given(self, collect_mod, psycopg2_mock):
        sql, params, _ = self._run(collect_mod, psycopg2_mock)
        assert "LIMIT %s" not in sql   # no top-level LIMIT
        assert 10 not in params  # no accidental limit


# ===========================================================================
# query_items — deduplication
# ===========================================================================

class TestQueryItemsDeduplication:
    def test_duplicate_hash_deduplication(self, collect_mod, psycopg2_mock):
        """Rows sharing the same duplicate_hash should collapse to first."""
        rows = [
            _default_row(id=1, duplicate_hash="HASH_A"),
            _default_row(id=2, duplicate_hash="HASH_A"),   # duplicate
            _default_row(id=3, duplicate_hash="HASH_B"),
        ]
        conn, cur = _make_db(rows)
        psycopg2_mock.connect.return_value = conn
        result = collect_mod.query_items()
        assert len(result) == 2
        ids = [r["id"] for r in result]
        assert 1 in ids
        assert 3 in ids
        assert 2 not in ids

    def test_null_hash_no_dedup(self, collect_mod, psycopg2_mock):
        """Rows with NULL duplicate_hash are deduplicated by id instead."""
        rows = [
            _default_row(id=1, duplicate_hash=None),
            _default_row(id=2, duplicate_hash=None),
        ]
        conn, cur = _make_db(rows)
        psycopg2_mock.connect.return_value = conn
        result = collect_mod.query_items()
        assert len(result) == 2


# ===========================================================================
# resolve_location
# ===========================================================================

class TestResolveLocation:
    """Uses in-memory rows; no second DB call needed."""

    def _db_with_geocoding(self, psycopg2_mock, rows):
        cur = MagicMock()
        cur.fetchall.return_value = rows
        conn = MagicMock()
        conn.cursor.return_value = cur
        psycopg2_mock.connect.return_value = conn

    def test_exact_country_match(self, collect_mod, psycopg2_mock):
        self._db_with_geocoding(psycopg2_mock, [
            (10, "Singapore", "Central", "Marina Bay"),
            (11, "Singapore", "West",    "Jurong"),
        ])
        ids = collect_mod.resolve_location("singapore")
        assert set(ids) == {10, 11}

    def test_no_match_raises_value_error(self, collect_mod, psycopg2_mock):
        self._db_with_geocoding(psycopg2_mock, [
            (10, "Singapore", "Central", "Marina Bay"),
        ])
        with pytest.raises(ValueError, match="not found"):
            collect_mod.resolve_location("Antarctica")

    def test_partial_match_raises_with_suggestions(self, collect_mod, psycopg2_mock):
        self._db_with_geocoding(psycopg2_mock, [
            (10, "France",   "Paris",   "Marais"),
            (11, "France",   "Lyon",    "Presqu'ile"),
        ])
        with pytest.raises(ValueError, match="Partial match"):
            collect_mod.resolve_location("mar")   # partial match, not exact

    def test_first_level_exact_match(self, collect_mod, psycopg2_mock):
        self._db_with_geocoding(psycopg2_mock, [
            (20, "France", "Paris", "Marais"),
        ])
        ids = collect_mod.resolve_location("Paris")
        assert 20 in ids


# ===========================================================================
# resolve_persons
# ===========================================================================

class TestResolvePersons:
    def _db_with_persons(self, psycopg2_mock, rows):
        cur = MagicMock()
        cur.fetchall.return_value = rows
        conn = MagicMock()
        conn.cursor.return_value = cur
        psycopg2_mock.connect.return_value = conn

    def test_exact_match(self, collect_mod, psycopg2_mock):
        self._db_with_persons(psycopg2_mock, [
            (1, "Alice"),
            (2, "Bob"),
        ])
        result = collect_mod.resolve_persons(["Alice"])
        assert result == {1: "Alice"}

    def test_case_insensitive_exact_match(self, collect_mod, psycopg2_mock):
        self._db_with_persons(psycopg2_mock, [(1, "Alice")])
        result = collect_mod.resolve_persons(["alice"])
        assert result == {1: "Alice"}

    def test_fuzzy_single_match(self, collect_mod, psycopg2_mock):
        self._db_with_persons(psycopg2_mock, [
            (1, "Alice Smith"),
            (2, "Bob Jones"),
        ])
        result = collect_mod.resolve_persons(["Smith"])
        assert result == {1: "Alice Smith"}

    def test_not_found_raises_value_error(self, collect_mod, psycopg2_mock):
        self._db_with_persons(psycopg2_mock, [(1, "Alice")])
        with pytest.raises(ValueError, match="not found"):
            collect_mod.resolve_persons(["Zaphod"])

    def test_ambiguous_raises_value_error(self, collect_mod, psycopg2_mock):
        self._db_with_persons(psycopg2_mock, [
            (1, "Alice A"),
            (2, "Alice B"),
        ])
        with pytest.raises(ValueError, match="Ambiguous"):
            collect_mod.resolve_persons(["Alice"])

    def test_multiple_names(self, collect_mod, psycopg2_mock):
        self._db_with_persons(psycopg2_mock, [
            (1, "Alice"),
            (2, "Bob"),
        ])
        result = collect_mod.resolve_persons(["Alice", "Bob"])
        assert result == {1: "Alice", 2: "Bob"}
