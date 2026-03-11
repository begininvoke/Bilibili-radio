import requests
import json

API_BASE = "http://localhost:5000"

print("=" * 60)
print("B站音频播放器 - 系统诊断")
print("=" * 60)

print("\n1. 检查API服务器状态...")
try:
    response = requests.get(f"{API_BASE}/status", timeout=2)
    result = response.json()
    if result.get('success'):
        print("✅ API服务器正常运行")
        print(f"   状态: {json.dumps(result.get('data'), indent=4, ensure_ascii=False)}")
    else:
        print("❌ API服务器返回错误")
except Exception as e:
    print(f"❌ 无法连接到API服务器: {e}")
    exit(1)

print("\n2. 测试获取视频信息...")
test_bvid = "BV1uz421X7bg"
try:
    response = requests.get(f"{API_BASE}/get_video_info/{test_bvid}", timeout=10)
    result = response.json()
    if result.get('success'):
        print(f"✅ 成功获取视频信息")
        print(f"   标题: {result['data'].get('title')}")
        print(f"   BV号: {result['data'].get('bvid')}")
        print(f"   CID: {result['data'].get('cid')}")
    else:
        print(f"❌ 获取视频信息失败: {result.get('message')}")
except Exception as e:
    print(f"❌ 请求失败: {e}")

print("\n3. 测试获取播放地址...")
test_cid = "1454380339"
try:
    response = requests.get(f"{API_BASE}/get_play_url/{test_bvid}/{test_cid}", timeout=10)
    result = response.json()
    if result.get('success'):
        print(f"✅ 成功获取播放地址")
        print(f"   URL: {result['data'].get('url')[:50]}...")
        print(f"   时长: {result['data'].get('duration')}ms")
        print(f"   码率: {result['data'].get('bitrate')}bps")
    else:
        print(f"❌ 获取播放地址失败: {result.get('message')}")
except Exception as e:
    print(f"❌ 请求失败: {e}")

print("\n4. 测试启动播放...")
try:
    audio_url = result['data']['url'] if result.get('success') else None
    if audio_url:
        play_data = {
            'audio_url': audio_url,
            'bvid': test_bvid
        }
        response = requests.post(f"{API_BASE}/start_play", json=play_data, timeout=10)
        result = response.json()
        if result.get('success'):
            print(f"✅ 播放启动成功")
            
            print("\n5. 等待3秒后检查播放状态...")
            import time
            time.sleep(3)
            
            try:
                response = requests.get(f"{API_BASE}/status", timeout=5)
                status = response.json()
                if status.get('success'):
                    data = status.get('data')
                    print(f"   Producer状态: {data.get('producer')}")
                    print(f"   Buffer状态: {data.get('buffer')}")
                    print(f"   Player状态: {data.get('player')}")
                else:
                    print(f"   ❌ 获取状态失败: {status.get('message')}")
            except Exception as e:
                print(f"   ⚠️ 状态检查超时或失败: {e}")
                print("   这可能表示FFmpeg正在处理音频流")

            print("\n6. 测试停止播放...")
            try:
                response = requests.post(f"{API_BASE}/stop_play", timeout=5)
                result = response.json()
                if result.get('success'):
                    print(f"✅ 播放已停止")
                else:
                    print(f"❌ 停止播放失败: {result.get('message')}")
            except Exception as e:
                print(f"❌ 停止播放失败: {e}")
        else:
            print(f"❌ 启动播放失败: {result.get('message')}")
    else:
        print("❌ 没有可用的音频URL")
except Exception as e:
    print(f"❌ 启动播放失败: {e}")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
