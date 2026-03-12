from enum import Enum


class ErrorCode(Enum):
    SUCCESS = 0
    UNKNOWN_ERROR = -1

    INVALID_BVID = 1001
    VIDEO_NOT_FOUND = 1002
    INVALID_INPUT = 1003
    NO_AUDIO_LOADED = 1004

    NETWORK_ERROR = 2001
    REQUEST_TIMEOUT = 2002

    API_ERROR = 3001
    NO_DASH_STREAM = 3002
    NO_AUDIO_STREAM = 3003


class ErrorMessage:
    INVALID_BVID = "无效的BV号格式"
    VIDEO_NOT_FOUND = "视频不存在"
    INVALID_INPUT = "无效的BV号或链接格式"
    INPUT_EMPTY = "请输入BV号或视频链接"
    NO_AUDIO_LOADED = "No audio loaded"

    NETWORK_ERROR = "网络请求失败"
    REQUEST_TIMEOUT = "请求超时"

    API_ERROR = "API请求错误"
    NO_DASH_STREAM = "无DASH流可用"
    NO_AUDIO_STREAM = "未找到音频流"

    PLAYBACK_FAILED = "播放失败"


class APIError(Exception):
    def __init__(self, code: ErrorCode, message: str = None):
        self.code = code
        self.message = message or self._get_default_message(code)
        super().__init__(self.message)

    @staticmethod
    def _get_default_message(code: ErrorCode) -> str:
        message_map = {
            ErrorCode.INVALID_BVID: ErrorMessage.INVALID_BVID,
            ErrorCode.VIDEO_NOT_FOUND: ErrorMessage.VIDEO_NOT_FOUND,
            ErrorCode.INVALID_INPUT: ErrorMessage.INVALID_INPUT,
            ErrorCode.NO_AUDIO_LOADED: ErrorMessage.NO_AUDIO_LOADED,
            ErrorCode.NETWORK_ERROR: ErrorMessage.NETWORK_ERROR,
            ErrorCode.REQUEST_TIMEOUT: ErrorMessage.REQUEST_TIMEOUT,
            ErrorCode.API_ERROR: ErrorMessage.API_ERROR,
            ErrorCode.NO_DASH_STREAM: ErrorMessage.NO_DASH_STREAM,
            ErrorCode.NO_AUDIO_STREAM: ErrorMessage.NO_AUDIO_STREAM,
        }
        return message_map.get(code, "未知错误")

    @classmethod
    def invalid_bvid(cls, bvid: str = None) -> "APIError":
        msg = f"Invalid BVID format: {bvid}" if bvid else ErrorMessage.INVALID_BVID
        return cls(ErrorCode.INVALID_BVID, msg)

    @classmethod
    def video_not_found(cls, bvid: str = None) -> "APIError":
        msg = f"Video not found: {bvid}" if bvid else ErrorMessage.VIDEO_NOT_FOUND
        return cls(ErrorCode.VIDEO_NOT_FOUND, msg)

    @classmethod
    def network_error(cls, detail: str = None) -> "APIError":
        msg = f"Network error: {detail}" if detail else ErrorMessage.NETWORK_ERROR
        return cls(ErrorCode.NETWORK_ERROR, msg)

    @classmethod
    def request_timeout(cls, bvid: str = None) -> "APIError":
        msg = f"Request timeout for BVID: {bvid}" if bvid else ErrorMessage.REQUEST_TIMEOUT
        return cls(ErrorCode.REQUEST_TIMEOUT, msg)

    @classmethod
    def api_error(cls, message: str = None) -> "APIError":
        return cls(ErrorCode.API_ERROR, message or ErrorMessage.API_ERROR)

    @classmethod
    def no_dash_stream(cls) -> "APIError":
        return cls(ErrorCode.NO_DASH_STREAM, ErrorMessage.NO_DASH_STREAM)

    @classmethod
    def no_audio_stream(cls) -> "APIError":
        return cls(ErrorCode.NO_AUDIO_STREAM, ErrorMessage.NO_AUDIO_STREAM)

    @classmethod
    def no_audio_loaded(cls) -> "APIError":
        return cls(ErrorCode.NO_AUDIO_LOADED, ErrorMessage.NO_AUDIO_LOADED)
