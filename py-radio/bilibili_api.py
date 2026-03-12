import re
import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class BilibiliAPIError(Exception):
    pass


class VideoNotFoundError(BilibiliAPIError):
    pass


class NetworkError(BilibiliAPIError):
    pass


@dataclass
class VideoInfo:
    bvid: str
    cid: int
    title: str
    duration: int
    owner: str
    cover: str


@dataclass
class AudioStreamInfo:
    url: str
    backup_urls: List[str]
    duration: int
    bitrate: int
    sample_rate: int
    channels: int
    init_range: str
    index_range: str


class BilibiliAPI:
    VIDEO_INFO_API = "https://api.bilibili.com/x/web-interface/view"
    PLAY_URL_API = "https://api.bilibili.com/x/player/playurl"

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    BV_PATTERN = re.compile(r"^(BV|bv)[0-9A-Za-z]{10}$")
    URL_PATTERN = re.compile(
        r"^(https?://)?(www\.)?bilibili\.com/video/(BV[0-9A-Za-z]{10})"
    )

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)

    @staticmethod
    def is_valid_bvid(bvid: str) -> bool:
        return bool(BilibiliAPI.BV_PATTERN.match(bvid))

    @staticmethod
    def extract_bvid(url: str) -> Optional[str]:
        match = BilibiliAPI.URL_PATTERN.search(url)
        return match.group(3) if match else None

    @staticmethod
    def parse_input(input_str: str) -> Optional[str]:
        input_str = input_str.strip()
        if BilibiliAPI.is_valid_bvid(input_str):
            return input_str.upper()

        bvid = BilibiliAPI.extract_bvid(input_str)
        if bvid:
            return bvid

        return None

    def get_video_info(self, bvid: str) -> VideoInfo:
        if not self.is_valid_bvid(bvid):
            raise ValueError(f"Invalid BVID format: {bvid}")

        params = {"bvid": bvid}
        headers = {**self.DEFAULT_HEADERS, "Referer": f"https://www.bilibili.com/video/{bvid}"}

        try:
            response = self.session.get(
                self.VIDEO_INFO_API,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("message", "Unknown error")
                if data.get("code") == -400:
                    raise VideoNotFoundError(f"Video not found: {bvid}")
                raise BilibiliAPIError(f"API error: {error_msg}")

            video_data = data.get("data", {})
            return VideoInfo(
                bvid=video_data.get("bvid", bvid),
                cid=video_data.get("cid", 0),
                title=video_data.get("title", ""),
                duration=video_data.get("duration", 0),
                owner=video_data.get("owner", {}).get("name", ""),
                cover=video_data.get("pic", ""),
            )

        except requests.Timeout:
            raise NetworkError(f"Request timeout for BVID: {bvid}")
        except requests.RequestException as e:
            raise NetworkError(f"Network error: {str(e)}")

    def get_audio_stream(self, bvid: str, cid: int, quality: int = 30280) -> AudioStreamInfo:
        if not self.is_valid_bvid(bvid):
            raise ValueError(f"Invalid BVID format: {bvid}")

        params = {
            "bvid": bvid,
            "cid": cid,
            "qn": 16,
            "fnval": 16,
            "fnver": 0,
            "fourk": 0,
        }

        headers = {**self.DEFAULT_HEADERS, "Referer": f"https://www.bilibili.com/video/{bvid}"}

        try:
            response = self.session.get(
                self.PLAY_URL_API,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("message", "Unknown error")
                raise BilibiliAPIError(f"API error: {error_msg}")

            play_data = data.get("data", {})

            if "dash" not in play_data:
                raise BilibiliAPIError("No DASH stream available")

            audio_streams = play_data.get("dash", {}).get("audio", [])
            if not audio_streams:
                raise BilibiliAPIError("No audio stream found")

            audio_stream = audio_streams[0]

            return AudioStreamInfo(
                url=audio_stream.get("baseUrl", ""),
                backup_urls=audio_stream.get("backupUrl", []),
                duration=play_data.get("timelength", 0) // 1000,
                bitrate=audio_stream.get("bandwidth", 0),
                sample_rate=audio_stream.get("sampleRate", 44100),
                channels=audio_stream.get("channel", 2),
                init_range=audio_stream.get("segmentBase", {}).get("initialization", ""),
                index_range=audio_stream.get("segmentBase", {}).get("indexRange", ""),
            )

        except requests.Timeout:
            raise NetworkError(f"Request timeout for BVID: {bvid}")
        except requests.RequestException as e:
            raise NetworkError(f"Network error: {str(e)}")

    def get_video_with_audio(self, input_str: str) -> tuple[VideoInfo, AudioStreamInfo]:
        bvid = self.parse_input(input_str)
        if not bvid:
            raise ValueError(f"Cannot parse BVID from input: {input_str}")

        video_info = self.get_video_info(bvid)
        audio_stream = self.get_audio_stream(bvid, video_info.cid)

        return video_info, audio_stream

    def close(self):
        self.session.close()


bilibili_api = BilibiliAPI()
