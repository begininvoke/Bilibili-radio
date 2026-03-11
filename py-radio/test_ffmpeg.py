import requests
import subprocess
import time

print("=" * 60)
print("FFmpeg音频流测试")
print("=" * 60)

API_BASE = "http://localhost:5000"
test_bvid = "BV1uz421X7bg"
test_cid = "1454380339"

print("\n1. 获取音频流URL...")
response = requests.get(f"{API_BASE}/get_play_url/{test_bvid}/{test_cid}", timeout=10)
result = response.json()

if not result.get('success'):
    print(f"❌ 获取失败: {result.get('message')}")
    exit(1)

audio_url = result['data']['url']
print(f"✅ 音频URL: {audio_url[:60]}...")

print("\n2. 测试FFmpeg直接播放...")
print("   正在启动FFmpeg...")

headers = [
    f'Referer: https://www.bilibili.com/video/{test_bvid}',
    f'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
]

cmd = ['ffmpeg']
for header in headers:
    cmd.extend(['-headers', header])

cmd.extend([
    '-i', audio_url,
    '-f', 's16le',
    '-acodec', 'pcm_s16le',
    '-ar', '44100',
    '-ac', '2',
    '-'
])

print(f"   命令: {' '.join(cmd[:10])}...")

try:
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    print("   ✅ FFmpeg进程已启动")
    print("   正在读取音频数据（5秒）...")
    
    time.sleep(2)
    
    total_bytes = 0
    start_time = time.time()
    
    while time.time() - start_time < 3:
        chunk = process.stdout.read(4096)
        if chunk:
            total_bytes += len(chunk)
            print(f"   读取到 {len(chunk)} 字节，总计 {total_bytes} 字节")
        else:
            print("   ⚠️ 没有读取到数据")
            break
    
    process.terminate()
    
    if total_bytes > 0:
        print(f"\n✅ 成功！共读取 {total_bytes} 字节音频数据")
        print("   音频流可以正常播放")
    else:
        print("\n❌ 失败！没有读取到音频数据")
        print("   可能的原因：")
        print("   1. 音频URL已过期")
        print("   2. 防盗链验证失败")
        print("   3. 网络连接问题")
        
        stderr_output = process.stderr.read().decode('utf-8', errors='ignore')
        if stderr_output:
            print(f"\n   FFmpeg错误输出:\n{stderr_output[:500]}")
            
except Exception as e:
    print(f"❌ 测试失败: {e}")

print("\n" + "=" * 60)
