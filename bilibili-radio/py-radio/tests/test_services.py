import tempfile
import unittest
from pathlib import Path

from bili_client import BiliClient
from library_service import LibraryService
from models import AudioStreamInfo, Track, make_track_id
from playback_service import PlaybackService
from settings_service import SettingsService
from stream_service import StreamService
from track_service import normalize_search_item, parse_duration


VALID_BVID = "BV1Q541167Qg"


class TrackServiceTests(unittest.TestCase):
    def test_parse_duration(self):
        self.assertEqual(parse_duration("03:25"), 205)
        self.assertEqual(parse_duration("01:02:03"), 3723)
        self.assertEqual(parse_duration(245), 245)

    def test_normalize_search_item(self):
        track = normalize_search_item(
            {
                "bvid": VALID_BVID,
                "title": "<em class=\"keyword\">Hello</em> World",
                "author": "tester",
                "pic": "//i0.hdslb.com/test.jpg",
                "duration": "04:05",
                "play": 123,
                "pubdate": 1784541600,
            }
        )

        self.assertEqual(track.bvid, VALID_BVID)
        self.assertEqual(track.title, "Hello World")
        self.assertEqual(track.cover, "https://i0.hdslb.com/test.jpg")
        self.assertEqual(track.duration, 245)
        self.assertEqual(track.play_count, 123)
        self.assertTrue(track.published_at.endswith("+08:00"))


class FakeResponse:
    def __init__(self, status_code=200, payload=None, reason="OK"):
        self.status_code = status_code
        self._payload = payload or {}
        self.reason = reason
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            error = requests.HTTPError(f"{self.status_code} {self.reason}")
            error.response = self
            raise error


class FakeSearchSession:
    def __init__(self):
        self.headers = {}
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        if url.endswith("bilibili.com/"):
            return FakeResponse()
        if len([call for call in self.calls if "search/type" in call]) == 1:
            return FakeResponse(status_code=412, payload={"code": -412, "message": "request was banned"}, reason="Precondition Failed")
        return FakeResponse(
            payload={
                "code": 0,
                "data": {
                    "result": [
                        {
                            "bvid": VALID_BVID,
                            "title": "Search Result",
                            "author": "UP",
                            "pic": "//i0.hdslb.com/a.jpg",
                            "duration": "01:02",
                            "play": 9,
                        }
                    ]
                },
            }
        )


class BiliClientTests(unittest.TestCase):
    def test_search_warms_guest_cookie_and_retries_412_once(self):
        client = BiliClient()
        client.session = FakeSearchSession()

        tracks = client.search("lofi", page=1, page_size=1)

        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0].bvid, VALID_BVID)
        self.assertEqual(client.session.calls.count(BiliClient.HOME_URL), 2)
        self.assertEqual(len([call for call in client.session.calls if "search/type" in call]), 2)

    def test_quality_selection_falls_back_to_available_stream(self):
        streams = [
            {"id": 30216, "bandwidth": 64000},
            {"id": 30232, "bandwidth": 128000},
        ]

        selected = BiliClient._select_audio_stream(streams, "high")

        self.assertEqual(selected["id"], 30232)


class LibraryServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.sqlite3"
        self.service = LibraryService(self.db_path)
        self.track = Track(
            bvid=VALID_BVID,
            cid=123,
            title="Test Track",
            owner="UP",
            duration=100,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_likes_recent_and_playlist_survive_new_service_instance(self):
        self.service.add_like(self.track)
        self.service.add_recent(self.track, position_ms=42_000, listen_ms=20_000)
        playlist = self.service.create_playlist("Inbox", tracks=[self.track])

        reloaded = LibraryService(self.db_path)
        self.assertEqual(len(reloaded.list_likes()), 1)
        self.assertEqual(reloaded.list_recent()[0]["positionMs"], 42_000)
        self.assertEqual(reloaded.get_playlist(playlist["id"])["tracks"][0]["trackId"], self.track.track_id)

    def test_batch_preview_and_add_deduplicates(self):
        playlist = self.service.create_playlist("Batch")
        preview = self.service.preview_playlist_items(
            playlist["id"],
            tracks=[self.track, self.track],
            track_ids=["missing"],
        )
        self.assertEqual(preview["total"], 3)
        self.assertEqual(preview["added"], 1)
        self.assertEqual(preview["duplicated"], 1)
        self.assertEqual(preview["unavailable"], 1)

        result = self.service.batch_add_playlist_items(playlist["id"], tracks=[self.track, self.track])
        self.assertEqual(result["added"], 1)
        self.assertEqual(result["duplicated"], 1)
        self.assertEqual(len(self.service.get_playlist(playlist["id"])["tracks"]), 1)

    def test_clear_recent_removes_recent_rows(self):
        self.service.add_recent(self.track, position_ms=42_000, listen_ms=20_000)
        self.assertEqual(len(self.service.list_recent()), 1)

        result = self.service.clear_recent()

        self.assertEqual(result["removed"], 1)
        self.assertEqual(self.service.list_recent(), [])


class SettingsServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.sqlite3"
        self.service = SettingsService(self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_audio_quality_preference_persists(self):
        self.assertEqual(self.service.get_audio_quality_preference(), "auto")

        self.service.set_audio_quality_preference("high")
        reloaded = SettingsService(self.db_path)

        self.assertEqual(reloaded.get_audio_quality_preference(), "high")

    def test_audio_quality_preference_rejects_invalid_values(self):
        with self.assertRaises(Exception):
            self.service.set_audio_quality_preference("lossless")


class PlaybackServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.sqlite3"
        self.library = LibraryService(self.db_path)
        self.track = Track(bvid=VALID_BVID, cid=123, title="Playable", duration=100)
        self.library.upsert_track(self.track)
        self.service = PlaybackService(self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_heartbeat_updates_recent_only_after_effective_listen(self):
        payload = {
            "sessionId": "s1",
            "trackId": self.track.track_id,
            "positionMs": 8_000,
            "listenMs": 10_000,
            "event": "heartbeat",
        }
        self.service.record_event(payload)
        self.assertEqual(self.service.list_recent(), [])

        payload["positionMs"] = 20_000
        payload["listenMs"] = 20_000
        self.service.record_event(payload)
        recent = self.service.list_recent()
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["trackId"], self.track.track_id)

    def test_completed_rule_uses_ninety_percent(self):
        result = self.service.record_event(
            {
                "sessionId": "s2",
                "trackId": self.track.track_id,
                "positionMs": 91_000,
                "listenMs": 50_000,
                "event": "end",
            }
        )
        self.assertTrue(result["completed"])

    def test_skip_under_effective_listen_does_not_enter_recent(self):
        result = self.service.record_event(
            {
                "sessionId": "s3",
                "trackId": self.track.track_id,
                "positionMs": 8_000,
                "listenMs": 8_000,
                "event": "skip",
            }
        )

        self.assertTrue(result["skipped"])
        self.assertEqual(self.service.list_recent(), [])


class FakeBiliClient:
    def __init__(self):
        self.calls = 0

    def get_video_info(self, bvid):
        raise AssertionError("cid should be supplied in this test")

    def get_audio_stream(self, bvid, cid, quality="auto"):
        self.calls += 1
        return AudioStreamInfo(
            url=f"https://example.test/{bvid}/{cid}.m4a",
            backup_urls=[],
            duration=100,
            bitrate=128000,
            sample_rate=44100,
            channels=2,
            quality=quality,
            actual_quality="standard",
            stream_id=30232,
        )


class StreamServiceTests(unittest.TestCase):
    def test_audio_info_cache_uses_bvid_cid_quality_alias(self):
        client = FakeBiliClient()
        service = StreamService(client, cache_ttl_seconds=60)

        first = service.get_audio_info(VALID_BVID, cid=123, quality="standard")
        second = service.get_audio_info(VALID_BVID, cid=123, quality="standard")
        third = service.get_audio_info(VALID_BVID, cid=123, quality="high")

        self.assertEqual(first.url, second.url)
        self.assertEqual(client.calls, 2)
        self.assertEqual(third.quality, "high")


class FakeAppStreamService:
    def __init__(self):
        self.last_quality = None

    def get_audio_info(self, bvid, cid=None, quality="auto"):
        self.last_quality = quality
        return AudioStreamInfo(
            url="https://example.test/audio.m4a",
            backup_urls=[],
            duration=100,
            bitrate=128000,
            sample_rate=44100,
            channels=2,
            quality=quality,
            actual_quality="standard",
            stream_id=30232,
        )


class AppEndpointTests(unittest.TestCase):
    def test_stream_info_returns_part_level_proxy_url(self):
        import app as app_module

        original_stream_service = app_module.stream_service
        app_module.stream_service = FakeAppStreamService()
        try:
            response = app_module.app.test_client().get(
                f"/api/tracks/{VALID_BVID}/123/stream-info?quality=high",
                base_url="http://127.0.0.1:5000",
            )
        finally:
            app_module.stream_service = original_stream_service

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["cid"], 123)
        self.assertEqual(
            payload["data"]["url"],
            f"http://127.0.0.1:5000/api/tracks/{VALID_BVID}/123/stream?quality=high",
        )

    def test_stream_info_uses_audio_quality_preference_when_quality_is_omitted(self):
        import app as app_module

        fake_stream_service = FakeAppStreamService()

        class FakeSettings:
            def get_audio_quality_preference(self):
                return "standard"

        original_stream_service = app_module.stream_service
        original_settings_service = app_module.settings_service
        app_module.stream_service = fake_stream_service
        app_module.settings_service = FakeSettings()
        try:
            response = app_module.app.test_client().get(
                f"/api/tracks/{VALID_BVID}/123/stream-info",
                base_url="http://127.0.0.1:5000",
            )
        finally:
            app_module.stream_service = original_stream_service
            app_module.settings_service = original_settings_service

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(fake_stream_service.last_quality, "standard")
        self.assertIn("quality=standard", payload["data"]["url"])

    def test_playlist_batch_endpoints_preview_and_write(self):
        import app as app_module

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.sqlite3"
            test_library = LibraryService(db_path)
            original_library_service = app_module.library_service
            app_module.library_service = test_library
            try:
                client = app_module.app.test_client()
                playlist = client.post(
                    "/api/library/playlists",
                    json={"name": "Batch API"},
                ).get_json()["data"]
                track = Track(bvid=VALID_BVID, cid=123, title="Batch Track").to_dict()

                preview = client.post(
                    f"/api/library/playlists/{playlist['id']}/items:preview",
                    json={"tracks": [track, track], "trackIds": ["missing"]},
                )
                write = client.post(
                    f"/api/library/playlists/{playlist['id']}/items:batch",
                    json={"tracks": [track, track], "trackIds": ["missing"]},
                )
            finally:
                app_module.library_service = original_library_service

        preview_payload = preview.get_json()
        write_payload = write.get_json()
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview_payload["data"]["added"], 1)
        self.assertEqual(preview_payload["data"]["duplicated"], 1)
        self.assertEqual(preview_payload["data"]["unavailable"], 1)
        self.assertEqual(write.status_code, 200)
        self.assertEqual(write_payload["data"]["added"], 1)


class ModelTests(unittest.TestCase):
    def test_make_track_id_is_part_level(self):
        self.assertEqual(make_track_id(VALID_BVID, 123), f"bili:{VALID_BVID}:cid:123")


if __name__ == "__main__":
    unittest.main()
