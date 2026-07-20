import tempfile
import unittest
from pathlib import Path

from library_service import LibraryService
from models import AudioStreamInfo, Track, make_track_id
from playback_service import PlaybackService
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


class ModelTests(unittest.TestCase):
    def test_make_track_id_is_part_level(self):
        self.assertEqual(make_track_id(VALID_BVID, 123), f"bili:{VALID_BVID}:cid:123")


if __name__ == "__main__":
    unittest.main()
