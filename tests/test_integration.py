"""
Integration tests against a live Synology NAS.

Run with:
    pytest tests/test_integration.py -v

These tests use real API calls. They verify correct behaviour both before
and after the synology-api refactor so regressions are caught immediately.

Known-good values (update if your NAS data changes):
    KNOWN_FOLDER_ID  = 166   (/GooglePhotosTakeout)
    KNOWN_PERSON_ID  = 88    (Yuer Guo, 2280+ photos)
    KNOWN_ITEM_ID    = 90885 (mmexport1771807937514.jpg)
    KNOWN_USERNAME   = yuerguo
"""

import json
import os
import tempfile
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Real IDs on this NAS — update if they change
# ---------------------------------------------------------------------------
KNOWN_FOLDER_ID  = 166
KNOWN_PERSON_ID  = 88
KNOWN_ITEM_ID    = 90885
KNOWN_ITEM_NAME  = "mmexport1771807937514.jpg"
KNOWN_USERNAME   = "yuerguo"
MIN_PERSON_COUNT = 500   # We know there are 592; allow some slack


def _nas_kwargs():
    """Build get_photos_api kwargs from environment variables."""
    return dict(
        nas_ip=os.getenv("NAS_IP"),
        nas_port=os.getenv("NAS_PORT"),
        nas_username=os.getenv("NAS_USERNAME"),
        nas_password=os.getenv("NAS_PASSWORD"),
        nas_secure=os.getenv("NAS_SECURE", "False").lower() == "true",
        nas_cert_verify=os.getenv("NAS_CERT_VERIFY", "False").lower() == "true",
        nas_dsm_version=int(os.getenv("NAS_DSM_VERSION", "7")),
        use_cache=True,
    )


def _list_persons_raw(photos, limit=10, additional=None):
    """Call SYNO.Foto.Browse.Person list and return the full response."""
    return photos.session.request_data(
        api_name="SYNO.Foto.Browse.Person",
        api_path="entry.cgi",
        req_param={
            "method": "list", "version": 1,
            "additional": json.dumps(additional or []),
            "offset": 0, "limit": limit,
            "show_more": False, "show_hidden": False,
        }
    )


# ---------------------------------------------------------------------------
# Shared session fixture (one login per test run)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def photos():
    """Return an authenticated Photos API instance."""
    from session_manager import get_photos_api
    instance, _ = get_photos_api(**_nas_kwargs())
    return instance


# ---------------------------------------------------------------------------
# Session / auth
# ---------------------------------------------------------------------------
class TestSession:
    def test_login_succeeds(self, photos):
        """Session object exists and has non-empty credentials."""
        assert photos.session.sid, "sid should not be empty"
        assert photos.session.syno_token, "syno_token should not be empty"

    def test_session_file_written(self):
        """Cache file is created after get_photos_api."""
        session_file = Path.home() / ".synology_photos_session"
        assert session_file.exists(), "Session file should exist after login"

    def test_session_file_has_required_keys(self):
        """Cache file contains sid, syno_token, created_at, last_used."""
        session_file = Path.home() / ".synology_photos_session"
        data = json.loads(session_file.read_text())
        for key in ("sid", "syno_token", "created_at", "last_used"):
            assert key in data, f"Session file missing key: {key}"

    def test_cached_session_reuse(self):
        """Second call to get_photos_api uses cache (no error)."""
        from session_manager import get_photos_api
        _, used_cache = get_photos_api(**_nas_kwargs())
        assert used_cache is True, "Second call should use cached session"


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class TestUser:
    @pytest.fixture(scope="class")
    def userinfo(self, photos):
        return photos.get_userinfo()

    def test_get_userinfo_success(self, userinfo):
        assert userinfo.get("success"), f"get_userinfo failed: {userinfo}"

    def test_get_userinfo_name(self, userinfo):
        assert userinfo["data"]["name"] == KNOWN_USERNAME

    def test_feature_get_user_info(self, photos, capsys):
        from features.user import get_user_info
        ok = get_user_info(photos)
        assert ok is True
        assert KNOWN_USERNAME in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Albums
# ---------------------------------------------------------------------------
class TestAlbums:
    @pytest.fixture(scope="class")
    def albums(self, photos):
        return photos.list_albums()

    def test_list_albums_success(self, albums):
        assert albums.get("success"), f"list_albums failed: {albums}"

    def test_list_albums_has_list_key(self, albums):
        assert "list" in albums["data"]

    def test_feature_list_albums_limit(self, photos, capsys):
        from features.albums import list_albums
        ok = list_albums(photos, limit=2)
        assert ok is True
        assert "Albums" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------
class TestFolders:
    @pytest.fixture(scope="class")
    def folder_list(self, photos):
        return photos.list_folders()

    @pytest.fixture(scope="class")
    def folder_detail(self, photos):
        return photos.get_folder(folder_id=KNOWN_FOLDER_ID)

    def test_list_folders_success(self, folder_list):
        assert folder_list.get("success"), f"list_folders failed: {folder_list}"

    def test_list_folders_non_empty(self, folder_list):
        assert len(folder_list["data"]["list"]) > 0

    def test_get_folder_success(self, folder_detail):
        assert folder_detail.get("success"), f"get_folder failed: {folder_detail}"

    def test_get_folder_correct_id(self, folder_detail):
        data = folder_detail.get("data", {}).get("folder", folder_detail.get("folder"))
        assert data is not None, "No folder data in response"

    def test_feature_list_folders(self, photos, capsys):
        from features.folders import list_folders
        ok = list_folders(photos, limit=2)
        assert ok is True
        assert "Folders" in capsys.readouterr().out

    def test_feature_get_folder(self, photos, capsys):
        from features.folders import get_folder
        ok = get_folder(photos, KNOWN_FOLDER_ID)
        assert ok is True
        assert str(KNOWN_FOLDER_ID) in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------
class TestItems:
    @pytest.fixture(scope="class")
    def items(self, photos):
        return photos.list_item_in_folders(folder_id=KNOWN_FOLDER_ID, limit=10)

    def test_list_items_in_folder_success(self, items):
        assert items.get("success"), f"list_item_in_folders failed: {items}"

    def test_list_items_returns_list(self, items):
        assert isinstance(items["data"]["list"], list)

    def test_feature_list_items_limit(self, photos, capsys):
        from features.items import list_items_in_folder
        ok = list_items_in_folder(photos, KNOWN_FOLDER_ID, limit=3)
        assert ok is True
        assert str(KNOWN_FOLDER_ID) in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Persons
# ---------------------------------------------------------------------------
class TestPersons:
    @pytest.fixture(scope="class")
    def all_persons(self, photos):
        """Fetch all persons once for the whole class."""
        return _list_persons_raw(photos, limit=2000)

    def test_list_persons_success(self, all_persons):
        assert all_persons.get("success"), f"list persons failed: {all_persons}"

    def test_list_persons_count(self, all_persons):
        total = len(all_persons["data"]["list"])
        assert total >= MIN_PERSON_COUNT, f"Expected >={MIN_PERSON_COUNT} persons, got {total}"

    def test_list_persons_has_item_count(self, all_persons):
        """Each person entry should have item_count field."""
        for person in all_persons["data"]["list"][:5]:
            assert "item_count" in person, f"Missing item_count in person: {person}"

    def test_known_person_exists(self, all_persons):
        """Known person ID 88 (Yuer Guo) should be in the list."""
        ids = [p["id"] for p in all_persons["data"]["list"]]
        assert KNOWN_PERSON_ID in ids, f"Person {KNOWN_PERSON_ID} not found"

    def test_feature_list_persons_limit(self, photos, capsys):
        from features.persons import list_persons
        ok = list_persons(photos, limit=3)
        assert ok is True
        assert "Persons" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Download — listing
# ---------------------------------------------------------------------------
class TestDownloadListing:
    @pytest.fixture(scope="class")
    def person_photos(self, photos):
        """Fetch person photos once — use limit=50 to cover all listing tests."""
        from features.download import get_person_photos
        return get_person_photos(photos, KNOWN_PERSON_ID, limit=50)

    def test_get_person_photos_success(self, person_photos):
        assert isinstance(person_photos, list)
        assert len(person_photos) > 0

    def test_get_person_photos_has_required_fields(self, person_photos):
        for item in person_photos[:3]:
            assert "id" in item, "Item missing 'id'"
            assert "filename" in item, "Item missing 'filename'"

    def test_get_person_photos_limit(self, person_photos):
        assert len(person_photos) <= 50

    def test_known_item_in_person_photos(self, person_photos):
        ids = [item["id"] for item in person_photos]
        assert KNOWN_ITEM_ID in ids, f"Item {KNOWN_ITEM_ID} not found in person {KNOWN_PERSON_ID}'s photos"

    def test_feature_list_person_photos(self, photos, capsys):
        from features.download import list_person_photos
        ok = list_person_photos(photos, KNOWN_PERSON_ID, limit=3)
        assert ok is True
        assert str(KNOWN_PERSON_ID) in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Download — actual file download
# ---------------------------------------------------------------------------
class TestDownloadFile:
    def test_download_single_item(self, photos):
        """Download one known photo and verify the file is written."""
        from features.download import download_item
        with tempfile.TemporaryDirectory() as tmpdir:
            ok = download_item(photos, KNOWN_ITEM_ID, KNOWN_ITEM_NAME, tmpdir)
            assert ok is True, "download_item returned False"
            output = Path(tmpdir) / KNOWN_ITEM_NAME
            assert output.exists(), "Downloaded file does not exist"
            assert output.stat().st_size > 0, "Downloaded file is empty"

    def test_download_file_size_reasonable(self, photos):
        """Downloaded file should be at least 1 MB (it's a 3.4 MB JPEG)."""
        from features.download import download_item
        with tempfile.TemporaryDirectory() as tmpdir:
            download_item(photos, KNOWN_ITEM_ID, KNOWN_ITEM_NAME, tmpdir)
            size_mb = (Path(tmpdir) / KNOWN_ITEM_NAME).stat().st_size / (1024 * 1024)
            assert size_mb >= 1.0, f"File too small ({size_mb:.1f} MB), may not be original"

    def test_download_person_photos_batch(self, photos):
        """Download 2 photos for a known person and check both land on disk."""
        from features.download import download_person_photos
        with tempfile.TemporaryDirectory() as tmpdir:
            ok = download_person_photos(photos, KNOWN_PERSON_ID, output_dir=tmpdir, limit=2)
            assert ok is True
            files = list(Path(tmpdir).iterdir())
            assert len(files) == 2, f"Expected 2 files, got {len(files)}"
            for f in files:
                assert f.stat().st_size > 0, f"{f.name} is empty"

    def test_invalid_item_id_returns_false(self, photos):
        """Downloading a non-existent item ID should return False gracefully."""
        from features.download import download_item
        with tempfile.TemporaryDirectory() as tmpdir:
            ok = download_item(photos, 9999999, "nonexistent.jpg", tmpdir)
            assert ok is False


# ---------------------------------------------------------------------------
# Person-count filter  (ground truth verified against DB on 2026-03-14)
# Counts are POST-deduplication (duplicate_hash), matching query_items() output.
# ---------------------------------------------------------------------------
#   none  = 55,533   (no face detected)
#   =1    =  7,673   (exactly 1 distinct person)
#   >=2   =  3,721   (2+ distinct persons)
#   =2    =  1,841   (exactly 2)
#   >=3   =  1,880   (3 or more)
#   none + =1 + >=2  == 66,927  (deduped total; grand total pre-dedup = 67,504)
#   =1  + person 88 (Yuer Guo) = 1,284
#   =1  + person 97 (Yi Zhang) = 1,574
#   >=2 + person 88             =   980
#   >=2 + person 97             =   974
# ---------------------------------------------------------------------------
PERSON_ID_YUER = 88
PERSON_ID_YI   = 97
MAX_QUERY_SECONDS = 6.0   # includes ~3s remote-DB + SELECT DISTINCT overhead;
                           # face join itself is <0.3s (verified via raw SQL)


class TestPersonCountFilter:

    def _q(self, person_count, person_ids=None, limit=None):
        """Run query_items with person_count filter, return (items, elapsed)."""
        import time
        from features.collect import query_items
        t = time.time()
        items = query_items(
            person_count=person_count,
            person_ids=person_ids or [],
            limit=limit,
        )
        return items, time.time() - t

    # --- counts ---

    def test_none_count(self):
        items, _ = self._q('none')
        assert len(items) == 55_533, f"Expected 55,533 got {len(items)}"

    def test_solo_count(self):
        items, _ = self._q('=1')
        assert len(items) == 7_673, f"Expected 7,673 got {len(items)}"

    def test_group_gte2_count(self):
        items, _ = self._q('>=2')
        assert len(items) == 3_721, f"Expected 3,721 got {len(items)}"

    def test_group_eq2_count(self):
        items, _ = self._q('=2')
        assert len(items) == 1_841, f"Expected 1,841 got {len(items)}"

    def test_group_gte3_count(self):
        items, _ = self._q('>=3')
        assert len(items) == 1_880, f"Expected 1,880 got {len(items)}"

    def test_all_buckets_are_fast(self):
        """Query speed test with limit=1 — isolates face-join latency from data transfer."""
        for pc in ('none', '=1', '>=2', '=2', '>=3'):
            _, elapsed = self._q(pc, limit=1)
            assert elapsed < MAX_QUERY_SECONDS, f"person_count={pc!r} too slow: {elapsed:.2f}s"

    def test_partitions_exhaustive(self):
        """none + solo + group must equal deduplicated total."""
        none  = len(self._q('none')[0])
        solo  = len(self._q('=1')[0])
        group = len(self._q('>=2')[0])
        assert none + solo + group == 66_927, (
            f"Partitions sum to {none + solo + group}, expected 66,927"
        )

    # --- correctness: spot-check a sample item from each bucket ---

    def _face_count(self, unit_id):
        """Direct DB face count for one unit (ground truth)."""
        import psycopg2
        conn = psycopg2.connect(
            host="192.168.1.169", port=5432, dbname="synofoto", user="postgres"
        )
        cur = conn.cursor()
        cur.execute(
            "SELECT count(DISTINCT id_person) FILTER (WHERE id_person IS NOT NULL)"
            "     + count(*) FILTER (WHERE id_person IS NULL)"
            " FROM face WHERE id_unit = %s",
            (unit_id,),
        )
        n = cur.fetchone()[0]
        conn.close()
        return n

    def test_none_sample_has_zero_faces(self):
        items, _ = self._q('none', limit=1)
        assert len(items) == 1
        assert self._face_count(items[0]['id']) == 0

    def test_solo_sample_has_one_face(self):
        items, _ = self._q('=1', limit=1)
        assert len(items) == 1
        assert self._face_count(items[0]['id']) == 1

    def test_group_sample_has_two_or_more_faces(self):
        items, _ = self._q('>=2', limit=1)
        assert len(items) == 1
        assert self._face_count(items[0]['id']) >= 2

    def test_eq2_sample_has_exactly_two_faces(self):
        items, _ = self._q('=2', limit=1)
        assert len(items) == 1
        assert self._face_count(items[0]['id']) == 2

    # --- named person combinations ---

    def test_solo_with_yuer(self):
        items, elapsed = self._q('=1', person_ids=[PERSON_ID_YUER])
        assert len(items) == 1_284, f"Expected 1,284 got {len(items)}"
        assert elapsed < MAX_QUERY_SECONDS

    def test_solo_with_yi_zhang(self):
        items, elapsed = self._q('=1', person_ids=[PERSON_ID_YI])
        assert len(items) == 1_574, f"Expected 1,574 got {len(items)}"
        assert elapsed < MAX_QUERY_SECONDS

    def test_group_with_yuer(self):
        items, elapsed = self._q('>=2', person_ids=[PERSON_ID_YUER])
        assert len(items) == 980, f"Expected 980 got {len(items)}"
        assert elapsed < MAX_QUERY_SECONDS

    def test_group_with_yi_zhang(self):
        items, elapsed = self._q('>=2', person_ids=[PERSON_ID_YI])
        assert len(items) == 974, f"Expected 974 got {len(items)}"
        assert elapsed < MAX_QUERY_SECONDS

    def test_solo_yuer_items_contain_yuer(self):
        """Every item from solo+Yuer must be linked to person 88."""
        import psycopg2
        items, _ = self._q('=1', person_ids=[PERSON_ID_YUER], limit=10)
        conn = psycopg2.connect(
            host="192.168.1.169", port=5432, dbname="synofoto", user="postgres"
        )
        cur = conn.cursor()
        for item in items:
            cur.execute(
                "SELECT 1 FROM many_unit_has_many_person WHERE id_unit=%s AND id_person=%s",
                (item['id'], PERSON_ID_YUER),
            )
            assert cur.fetchone(), f"Unit {item['id']} missing person {PERSON_ID_YUER}"
        conn.close()

    def test_none_has_no_named_persons(self):
        """Items with no face should not appear in many_unit_has_many_person."""
        import psycopg2
        items, _ = self._q('none', limit=20)
        ids = [i['id'] for i in items]
        conn = psycopg2.connect(
            host="192.168.1.169", port=5432, dbname="synofoto", user="postgres"
        )
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM many_unit_has_many_person WHERE id_unit = ANY(%s)",
            (ids,),
        )
        assert cur.fetchone()[0] == 0
        conn.close()

    # --- legacy format backward compat ---

    def test_legacy_2plus_format(self):
        """Old '2+' string must still work and match >=2 count."""
        items_legacy, elapsed = self._q('2+')
        assert len(items_legacy) == 3_721, f"Legacy '2+' got {len(items_legacy)}"
        assert elapsed < MAX_QUERY_SECONDS
