import re

from ringbuffer import AudioRingBuffer  
from flask import Flask
from Result import Result
from ErrorConstant import *
from constant import (
    BILIBILI_VIDEO_INFO_API,
    BILIBILI_PLAY_URL_API,
    DEFAULT_HEADERS,    
)
import requests


def is_valid_bvid(bvid):
    pattern = r'^(BV|bv)[0-9A-Za-z]{10}$'
    return re.match(pattern, bvid) is not None

def is_valid_Bilibili_url(url):
    pattern = r'^(https?|ftp)://www\.bilibili\.com/video/(BV[0-9A-Za-z]{10})(/.*)?$'
    return re.match(pattern, url) is not None

app = Flask(__name__)

def extract_bvid_from_url(url):
    res = url.split('/video/')
    if len(res) > 1:    
        return res[1].split('/')[0]
    else:
        return None
    
@app.route('/get_video_info/<bvid>', methods=['GET'])
def get_video_info(bvid):
    if not is_valid_bvid(bvid):
        return Result.error(INVALID_URL_ERROR_MSG).to_dict()
    info_url = BILIBILI_VIDEO_INFO_API.format(bvid=bvid)
    res = requests.get(info_url, headers=DEFAULT_HEADERS,stream=True)
    datas = res.json()
    if datas['code'] != 0:
        return Result.error(VIDEO_INFO_ERROR_MSG)
    data = datas['data']
    # 只保留 bvid、cid、title 字段
    filtered = {
        'bvid': data.get('bvid'),
        'cid': data.get('cid'),
        'title': data.get('title')
    }
    return Result.success(filtered)

@app.route('/get_play_url/<bvid>/<cid>', methods=['GET'])
def get_play_url(bvid, cid):
    if not is_valid_bvid(bvid):
        return Result.error(INVALID_URL_ERROR_MSG).to_dict()
    play_url = BILIBILI_PLAY_URL_API.format(bvid=bvid, cid=cid)
    res = requests.get(play_url, headers=DEFAULT_HEADERS,stream=True)
    data = res.json()['data']
    # 提取音频流（取最高音质）
    audio_stream = data['dash']['audio'][0]
    
    return Result.success({
        'url': audio_stream['baseUrl'],
        'backup_urls': audio_stream['backupUrl'],  # 备用线路
        'init_range': audio_stream['segmentBase']['initialization'],#range的初始和长度
        'index_range': audio_stream['segmentBase']['indexRange'],
        # 播放器 UI 信息
        'duration': data['timelength'],      # 总时长
        'bitrate': audio_stream['bandwidth'],# 码率
        # Seek 策略参考
        'seek_type': data.get('seek_type', 'offset'),
    })


#下载
@app.route('/download', methods=['GET'])
def download():
    data = requests.get_json()
    url = data.get('audio_url')
    headers = DEFAULT_HEADERS
    download_worker(url, headers)
    return Result.ok()


def download_worker(url, headers):
    audio_buffer = AudioRingBuffer()  # 使用完善的AudioRingBuffer
    resp = requests.get(url, headers=headers, stream=True)
    if resp.status_code == 200:
        audio_buffer.start_monitoring(interval=3)  # 启动监控线程，3秒刷新一次
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                # 阻塞式写入，自动丢弃最老数据，通知消费者
                audio_buffer.write(chunk)
        # 下载结束后可清理或停止监控
        audio_buffer.stop()
    else:
        print(f"下载失败，状态码: {resp.status_code}")