DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bilibili.com/video/{bvid}"
}

BILIBILI_VIDEO_INFO_API = "https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
BILIBILI_PLAY_URL_API = "https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=112&fnval=16"