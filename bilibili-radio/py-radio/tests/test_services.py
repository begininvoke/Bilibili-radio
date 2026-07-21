import tempfile
import unittest
from pathlib import Path

from analysis_service import AnalysisService
from auth_service import AuthService
from bili_client import BiliClient
from constant import BilibiliAPI as APIConst
from database import get_connection
from library_service import LibraryService
from models import AudioStreamInfo, Track, make_track_id
from playback_service import PlaybackService
from queue_service import PlayerQueueService
from settings_service import SettingsService
from stream_service import StreamService
from track_service import (
    cover_info_from_video_data,
    normalize_player_chapters,
    normalize_player_subtitles,
    normalize_reply_comments,
    normalize_search_item,
    normalize_subtitle_lines,
    normalize_video_detail,
    normalize_video_intro,
    parse_duration,
)


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

    def test_video_detail_uses_page_first_frame_as_track_cover(self):
        detail = normalize_video_detail(
            {
                "bvid": VALID_BVID,
                "cid": 1,
                "title": "Multi Part",
                "pic": "http://i0.hdslb.com/video.jpg",
                "owner": {"name": "UP"},
                "pages": [
                    {"cid": 1, "page": 1, "part": "P1", "duration": 60, "first_frame": "//i0.hdslb.com/p1.jpg"},
                    {"cid": 2, "page": 2, "part": "P2", "duration": 60},
                ],
            }
        )

        self.assertEqual(detail.pages[0].cover, "https://i0.hdslb.com/p1.jpg")
        self.assertEqual(detail.pages[1].cover, "https://i0.hdslb.com/video.jpg")


class FakeCookie:
    def __init__(self, name, value):
        self.name = name
        self.value = value


class FakeResponse:
    def __init__(self, status_code=200, payload=None, reason="OK", cookies=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.reason = reason
        self.headers = {"content-type": "application/json"}
        self.cookies = cookies or []

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

    def test_favorite_tracks_are_normalized_and_authenticated(self):
        class FavoriteSession:
            def __init__(self):
                self.headers = {}
                self.last_headers = None

            def get(self, url, **kwargs):
                self.last_headers = kwargs.get("headers")
                if url != APIConst.FAVORITE_RESOURCE_URL:
                    raise AssertionError(f"Unexpected URL: {url}")
                return FakeResponse(
                    payload={
                        "code": 0,
                        "data": {
                            "info": {
                                "id": 12,
                                "title": "Fav",
                                "media_count": 2,
                                "cover": "//i0.hdslb.com/fav.jpg",
                            },
                            "has_more": False,
                            "medias": [
                                {
                                    "bvid": VALID_BVID,
                                    "title": "Fav Track",
                                    "cover": "//i0.hdslb.com/cover.jpg",
                                    "duration": 62,
                                    "upper": {"name": "UP"},
                                    "cnt_info": {"play": 9},
                                    "pubtime": 1784541600,
                                },
                                {"title": "Unavailable"},
                            ],
                        },
                    }
                )

        session = FavoriteSession()
        client = BiliClient(cookie_provider=lambda: "SESSDATA=abc")
        client.session = session

        result = client.list_favorite_tracks(12)

        self.assertEqual(result["folder"]["title"], "Fav")
        self.assertEqual(result["tracks"][0]["bvid"], VALID_BVID)
        self.assertEqual(result["tracks"][0]["cover"], "https://i0.hdslb.com/cover.jpg")
        self.assertEqual(result["unavailable"], 1)
        self.assertEqual(session.last_headers["Cookie"], "SESSDATA=abc")


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


class PlayerQueueServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.sqlite3"
        self.service = PlayerQueueService(self.db_path)
        self.tracks = [
            Track(bvid=VALID_BVID, cid=123, title="P1", owner="UP", duration=100),
            Track(bvid=VALID_BVID, cid=456, title="P2", owner="UP", duration=120),
        ]

    def tearDown(self):
        self.tmp.cleanup()

    def test_queue_snapshot_survives_new_service_instance(self):
        saved = self.service.save_queue(self.tracks, current_index=1, play_mode="loop")

        reloaded = PlayerQueueService(self.db_path).get_queue()

        self.assertEqual(saved["currentIndex"], 1)
        self.assertEqual(reloaded["playMode"], "loop")
        self.assertEqual([track["cid"] for track in reloaded["queue"]], [123, 456])

    def test_empty_queue_keeps_state_row_to_avoid_local_resurrection(self):
        self.service.save_queue(self.tracks, current_index=0, play_mode="shuffle")
        cleared = self.service.clear_queue()

        self.assertEqual(cleared["queue"], [])
        self.assertEqual(cleared["currentIndex"], -1)
        self.assertIsNotNone(cleared["updatedAt"])


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.sqlite3"

    def tearDown(self):
        self.tmp.cleanup()

    def test_qr_poll_success_saves_encrypted_cookie_and_profile(self):
        class AuthSession:
            def __init__(self):
                self.headers = {}

            def get(self, url, **kwargs):
                if url == APIConst.QR_GENERATE_URL:
                    return FakeResponse(
                        payload={
                            "code": 0,
                            "data": {
                                "url": "https://account.bilibili.com/scan?qrcode_key=key1",
                                "qrcode_key": "key1",
                            },
                        }
                    )
                if url == APIConst.QR_POLL_URL:
                    return FakeResponse(
                        payload={"code": 0, "data": {"code": 0, "refresh_token": "rt1"}},
                        cookies=[
                            FakeCookie("SESSDATA", "abc"),
                            FakeCookie("DedeUserID", "123"),
                        ],
                    )
                if url == APIConst.NAV_URL:
                    return FakeResponse(
                        payload={
                            "code": 0,
                            "data": {
                                "isLogin": True,
                                "mid": 123,
                                "uname": "Tester",
                                "face": "//i0.hdslb.com/face.jpg",
                                "level_info": {"current_level": 5},
                                "vip": {"type": 2},
                            },
                        }
                    )
                raise AssertionError(f"Unexpected URL: {url}")

        service = AuthService(self.db_path, session=AuthSession())
        qr = service.create_qrcode()
        result = service.poll_qrcode(qr["qrcodeKey"])

        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(result["user"]["mid"], 123)
        self.assertEqual(service.get_cookie_header(), "SESSDATA=abc; DedeUserID=123")
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT cookie_encrypted FROM auth_state").fetchone()
        self.assertNotIn("SESSDATA=abc", row["cookie_encrypted"])


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


class AnalysisServiceTests(unittest.TestCase):
    def test_record_event_persists_analysis_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.sqlite3"
            service = AnalysisService(db_path)
            result = service.record_event(
                {
                    "event": "favorite_imported",
                    "trackId": f"bili:{VALID_BVID}:cid:123",
                    "payload": {"added": 1},
                }
            )

            with get_connection(db_path) as conn:
                row = conn.execute("SELECT event, track_id FROM analysis_events").fetchone()

        self.assertGreater(result["id"], 0)
        self.assertEqual(row["event"], "favorite_imported")
        self.assertEqual(row["track_id"], f"bili:{VALID_BVID}:cid:123")


class CoverInfoTests(unittest.TestCase):
    def test_cover_info_returns_video_cover_and_page_first_frame(self):
        result = cover_info_from_video_data(
            {
                "bvid": VALID_BVID,
                "pic": "http://i0.hdslb.com/bfs/archive/main.jpg",
                "owner": {"face": "//i0.hdslb.com/face.jpg"},
                "pages": [
                    {"cid": 1, "page": 1, "part": "P1", "first_frame": "//i0.hdslb.com/p1.jpg"},
                    {"cid": 2, "page": 2, "part": "P2", "first_frame": "http://i1.hdslb.com/p2.jpg"},
                ],
            },
            cid=2,
        )

        self.assertEqual(result["videoCover"], "https://i0.hdslb.com/bfs/archive/main.jpg")
        self.assertEqual(result["cover"], "https://i1.hdslb.com/p2.jpg")
        self.assertEqual(result["pageCover"], "https://i1.hdslb.com/p2.jpg")
        self.assertEqual(result["pages"][0]["firstFrame"], "https://i0.hdslb.com/p1.jpg")


class TrackDetailPanelTests(unittest.TestCase):
    def test_intro_normalizes_description_stats_and_pages(self):
        result = normalize_video_intro(
            {
                "bvid": VALID_BVID,
                "cid": 1,
                "title": "Title",
                "desc": "Line 1\nLine 2",
                "dynamic": "Dynamic",
                "pubdate": 1784541600,
                "owner": {"mid": 7, "name": "UP", "face": "//i0.hdslb.com/face.jpg"},
                "stat": {"view": 100, "reply": 3, "like": 9},
                "pages": [{"cid": 1, "page": 1, "part": "Part", "duration": 62}],
            }
        )

        self.assertEqual(result["description"], "Line 1\nLine 2")
        self.assertEqual(result["owner"]["face"], "https://i0.hdslb.com/face.jpg")
        self.assertEqual(result["stats"]["view"], 100)
        self.assertEqual(result["pages"][0]["title"], "Part")

    def test_subtitle_and_chapter_payloads_are_frontend_ready(self):
        player_data = {
            "need_login_subtitle": False,
            "subtitle": {
                "subtitles": [
                    {
                        "id": 1,
                        "lan": "zh-CN",
                        "lan_doc": "中文",
                        "subtitle_url": "//i0.hdslb.com/subtitle.json",
                    }
                ]
            },
            "view_points": [{"from": 1, "to": 3, "content": "Hook", "imgUrl": "//i0.hdslb.com/c.jpg"}],
        }

        subtitles = normalize_player_subtitles(
            player_data,
            VALID_BVID,
            123,
            lines=normalize_subtitle_lines({"body": [{"from": 1.2, "to": 2.5, "content": "<b>Hi</b>"}]}),
            selected_subtitle_id=1,
        )
        chapters = normalize_player_chapters(player_data, VALID_BVID, 123)

        self.assertEqual(subtitles["subtitles"][0]["url"], "https://i0.hdslb.com/subtitle.json")
        self.assertEqual(subtitles["lines"][0]["text"], "Hi")
        self.assertEqual(chapters["chapters"][0]["title"], "Hook")

    def test_comments_are_normalized(self):
        result = normalize_reply_comments(
            {
                "data": {
                    "cursor": {"all_count": 10, "is_end": False},
                    "replies": [
                        {
                            "rpid": 99,
                            "member": {"mid": 8, "uname": "User", "avatar": "//i0.hdslb.com/a.jpg"},
                            "content": {"message": "Nice"},
                            "like": 4,
                            "rcount": 2,
                            "ctime": 1784541600,
                        }
                    ],
                }
            },
            VALID_BVID,
            100,
            1,
            20,
        )

        self.assertEqual(result["total"], 10)
        self.assertTrue(result["hasMore"])
        self.assertEqual(result["comments"][0]["author"]["avatar"], "https://i0.hdslb.com/a.jpg")


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

    def test_image_proxy_host_allowlist(self):
        import app as app_module

        self.assertTrue(app_module._is_allowed_image_host("i0.hdslb.com"))
        self.assertTrue(app_module._is_allowed_image_host("member.bilibili.com"))
        self.assertFalse(app_module._is_allowed_image_host("example.com"))


class ModelTests(unittest.TestCase):
    def test_make_track_id_is_part_level(self):
        self.assertEqual(make_track_id(VALID_BVID, 123), f"bili:{VALID_BVID}:cid:123")


if __name__ == "__main__":
    unittest.main()
