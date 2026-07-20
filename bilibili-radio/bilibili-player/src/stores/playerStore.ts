import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  VideoInfo,
  PlayerStatus,
  PlayMode,
  Track,
  DownloadProgress,
  PlaybackProgress,
  AudioStreamInfo,
} from '@/types'
import {
  apiUrl,
  getTrackDetail,
  getTrackStreamInfo,
  resetStreamStats,
  resolveTrackInput,
} from '@/api/client'
import { wsClient } from '@/audio/WsClient'
import { streamingAudioPlayer } from '@/audio/StreamingAudioPlayer'
import { useLibraryStore } from '@/stores/libraryStore'

interface StreamStats {
  total_bytes: number
  session_bytes: number
  elapsed_seconds: number
  bytes_per_second: number
  total_mb: number
  session_mb: number
}

const PLAY_MODES: PlayMode[] = ['order', 'loop', 'single', 'shuffle']

export const usePlayerStore = defineStore('player', () => {
  const status = ref<PlayerStatus>('idle')
  const currentTime = ref(0)
  const duration = ref(0)
  const volume = ref(0.8)
  const isMuted = ref(false)
  const bufferLevel = ref(0)
  const videoInfo = ref<VideoInfo | null>(null)
  const errorMessage = ref<string | null>(null)
  const statusMessage = ref<string>('')
  const downloadProgress = ref<DownloadProgress | null>(null)
  const isConnected = ref(false)
  const isInitialized = ref(false)
  const streamStats = ref<StreamStats | null>(null)
  const isDownloading = ref(false)

  // 播放队列
  const queue = ref<Track[]>([])
  const currentIndex = ref(-1)
  const playMode = ref<PlayMode>('order')

  let statsInterval: ReturnType<typeof setInterval> | null = null
  let playSeq = 0

  const currentTrack = computed<Track | null>(() => {
    if (currentIndex.value < 0 || currentIndex.value >= queue.value.length) return null
    return queue.value[currentIndex.value]
  })
  const formattedCurrentTime = computed(() => formatTime(currentTime.value))
  const formattedDuration = computed(() => formatTime(duration.value))
  const progress = computed(() => {
    if (duration.value === 0) return 0
    return (currentTime.value / duration.value) * 100
  })
  const bufferPercent = computed(() => bufferLevel.value * 100)
  const isPlaying = computed(() => status.value === 'playing')
  const isPaused = computed(() => status.value === 'paused')
  const isLoading = computed(() => status.value === 'loading')
  const hasError = computed(() => status.value === 'error')
  const hasTrack = computed(() => currentTrack.value !== null || videoInfo.value !== null)
  const formattedStreamStats = computed(() => {
    if (!streamStats.value) return null
    return {
      sessionMB: streamStats.value.session_mb.toFixed(2),
      totalMB: streamStats.value.total_mb.toFixed(2),
      speed: formatSpeed(streamStats.value.bytes_per_second),
    }
  })

  function formatSpeed(bytesPerSecond: number): string {
    if (bytesPerSecond < 1024) {
      return `${bytesPerSecond.toFixed(0)} B/s`
    } else if (bytesPerSecond < 1024 * 1024) {
      return `${(bytesPerSecond / 1024).toFixed(1)} KB/s`
    } else {
      return `${(bytesPerSecond / (1024 * 1024)).toFixed(2)} MB/s`
    }
  }

  function formatTime(seconds: number): string {
    if (!Number.isFinite(seconds) || seconds < 0) seconds = 0
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  async function fetchStreamStats() {
    try {
      const response = await fetch(apiUrl('/api/stream/stats'))
      const data = await response.json()
      if (data.success) {
        streamStats.value = data.data
      }
    } catch (error) {
      console.error('Failed to fetch stream stats:', error)
    }
  }

  function startStatsPolling() {
    if (statsInterval) {
      clearInterval(statsInterval)
    }
    statsInterval = setInterval(fetchStreamStats, 1000)
  }

  function stopStatsPolling() {
    if (statsInterval) {
      clearInterval(statsInterval)
      statsInterval = null
    }
  }

  async function initialize() {
    if (isInitialized.value) return

    const playerReady = streamingAudioPlayer.init()
    if (!playerReady) {
      setError('音频播放器初始化失败')
      return
    }

    streamingAudioPlayer.onStateChange((playing) => {
      if (playing) {
        status.value = 'playing'
        startStatsPolling()
      } else {
        if (status.value === 'playing') {
          status.value = 'paused'
        }
      }
    })

    streamingAudioPlayer.onTimeUpdate((time, dur) => {
      currentTime.value = time
      if (dur > 0 && dur !== duration.value) {
        duration.value = dur
      }
    })

    streamingAudioPlayer.onEnded(() => {
      handleTrackEnded()
    })

    streamingAudioPlayer.onError((error) => {
      setError(error)
    })

    streamingAudioPlayer.onCanPlay(() => {
      streamingAudioPlayer.play()
    })

    streamingAudioPlayer.setVolume(volume.value)

    wsClient.setCallbacks({
      onVideoInfo: (info: VideoInfo) => {
        videoInfo.value = info
        duration.value = info.duration
        status.value = 'loading'
        statusMessage.value = '正在加载音频...'
        syncCurrentTrackFromInfo(info)
      },
      onAudioStream: (streamInfo: AudioStreamInfo) => {
        streamingAudioPlayer.loadStream(streamInfo)
      },
      onDownloadProgress: (progress: DownloadProgress) => {
        downloadProgress.value = progress
      },
      onPlaybackProgress: (progress: PlaybackProgress) => {
        currentTime.value = progress.current_time
        bufferLevel.value = progress.buffer_level

        if (progress.error) {
          setError(progress.error)
        }
      },
      onStatus: (message: string) => {
        statusMessage.value = message
      },
      onError: (message: string) => {
        setError(message)
      },
      onProducerState: (state: string) => {
        console.log('Producer state:', state)
      },
      onConsumerState: (state: string) => {
        console.log('Consumer state:', state)
        if (state === 'playing') {
          status.value = 'playing'
        } else if (state === 'paused') {
          status.value = 'paused'
        } else if (state === 'stopped') {
          status.value = 'idle'
          currentTime.value = 0
        } else if (state === 'error') {
          status.value = 'error'
        }
      },
    })

    const connected = await wsClient.connect()
    isConnected.value = connected

    if (!connected) {
      console.warn('Socket.IO is unavailable; HTTP playback remains enabled')
    }

    isInitialized.value = true
  }

  function setError(message: string) {
    errorMessage.value = message
    status.value = 'error'
  }

  function clearError() {
    errorMessage.value = null
  }

  /** 用服务端返回的视频信息补全队列中当前曲目缺失的字段（封面 / UP主 / 时长） */
  function syncCurrentTrackFromInfo(info: VideoInfo) {
    const library = useLibraryStore()
    const track: Track = {
      trackId: info.trackId,
      bvid: info.bvid,
      cid: info.cid,
      title: info.title,
      owner: info.owner,
      cover: info.cover,
      duration: info.duration,
      playCount: info.playCount,
      publishedAt: info.publishedAt,
    }
    const idx = findTrackIndex(track)
    if (idx >= 0) {
      queue.value[idx] = { ...queue.value[idx], ...track }
      currentIndex.value = idx
    } else {
      queue.value.push(track)
      currentIndex.value = queue.value.length - 1
    }
    library.addRecent(track)
  }

  async function requestPlayTrack(track: Track) {
    const seq = ++playSeq
    clearError()
    status.value = 'loading'
    statusMessage.value = '正在获取视频信息...'
    currentTime.value = 0
    streamingAudioPlayer.stop()

    if (!isInitialized.value) {
      await initialize()
    }

    try {
      const playableTrack = await resolvePlayableTrack(track)
      if (seq !== playSeq) return

      syncQueueCurrentTrack(playableTrack)
      videoInfo.value = trackToVideoInfo(playableTrack)
      duration.value = playableTrack.duration
      statusMessage.value = '正在解析音频流...'

      await resetStreamStats().catch((error) => {
        console.warn('Failed to reset stream stats:', error)
      })
      const streamInfo = await getTrackStreamInfo(playableTrack.bvid, playableTrack.cid)
      if (seq !== playSeq) return

      statusMessage.value = '正在缓冲音频...'
      streamingAudioPlayer.loadStream(streamInfo)
      useLibraryStore().addRecent(playableTrack)
    } catch (error) {
      if (seq !== playSeq) return
      setError(error instanceof Error ? error.message : '播放失败')
    }
  }

  /** 直接输入 BV/URL 播放：作为新曲目加入队列并播放 */
  async function playInput(input: string) {
    const value = input.trim()
    if (!value) {
      setError('请输入BV号或视频链接')
      return
    }
    clearError()
    status.value = 'loading'
    statusMessage.value = '正在解析输入...'
    try {
      const detail = await resolveTrackInput(value)
      const track = detail.pages[0] ?? detail.track
      const idx = findTrackIndex(track)
      if (idx >= 0) {
        currentIndex.value = idx
      } else {
        queue.value.push(track)
        currentIndex.value = queue.value.length - 1
      }
      await requestPlayTrack(track)
    } catch (error) {
      setError(error instanceof Error ? error.message : '无法解析输入')
    }
  }

  /** 播放一条已知曲目（来自搜索结果、收藏、歌单等），若不在队列则追加 */
  function playTrack(track: Track) {
    const idx = findTrackIndex(track)
    if (idx >= 0) {
      currentIndex.value = idx
    } else {
      queue.value.push(track)
      currentIndex.value = queue.value.length - 1
    }
    void requestPlayTrack(track)
  }

  /** 用一组曲目替换队列并从指定位置开始播放 */
  function playList(tracks: Track[], startIndex = 0) {
    if (tracks.length === 0) return
    queue.value = [...tracks]
    currentIndex.value = Math.max(0, Math.min(startIndex, tracks.length - 1))
    void requestPlayTrack(queue.value[currentIndex.value])
  }

  /** 追加到队列末尾，不打断当前播放 */
  function enqueue(track: Track) {
    if (queue.value.some((t) => isSameTrack(t, track))) return
    queue.value.push(track)
    if (currentIndex.value === -1) {
      currentIndex.value = 0
      void requestPlayTrack(track)
    }
  }

  function playAt(index: number) {
    if (index < 0 || index >= queue.value.length) return
    currentIndex.value = index
    void requestPlayTrack(queue.value[index])
  }

  function removeFromQueue(index: number) {
    if (index < 0 || index >= queue.value.length) return
    queue.value.splice(index, 1)
    if (index < currentIndex.value) {
      currentIndex.value--
    } else if (index === currentIndex.value) {
      // 删除的是当前曲目：停止并将索引钳制到合法范围
      if (queue.value.length === 0) {
        stop()
      } else {
        currentIndex.value = Math.min(currentIndex.value, queue.value.length - 1)
      }
    }
  }

  function clearQueue() {
    stop()
    queue.value = []
    currentIndex.value = -1
  }

  function nextIndex(): number {
    const len = queue.value.length
    if (len === 0) return -1
    if (playMode.value === 'shuffle') {
      if (len === 1) return currentIndex.value
      let n = currentIndex.value
      while (n === currentIndex.value) {
        n = Math.floor(Math.random() * len)
      }
      return n
    }
    const next = currentIndex.value + 1
    if (next >= len) {
      // order 模式到末尾停止，loop 模式回到开头
      return playMode.value === 'loop' ? 0 : -1
    }
    return next
  }

  function prevIndex(): number {
    const len = queue.value.length
    if (len === 0) return -1
    if (playMode.value === 'shuffle') {
      if (len === 1) return currentIndex.value
      let n = currentIndex.value
      while (n === currentIndex.value) {
        n = Math.floor(Math.random() * len)
      }
      return n
    }
    const prev = currentIndex.value - 1
    if (prev < 0) {
      return playMode.value === 'loop' ? len - 1 : 0
    }
    return prev
  }

  function next() {
    const n = nextIndex()
    if (n === -1) {
      // 顺序播放到底
      status.value = 'idle'
      currentTime.value = 0
      return
    }
    playAt(n)
  }

  function prev() {
    // 播放超过 3 秒时，上一首先回到开头
    if (currentTime.value > 3) {
      seek(0)
      return
    }
    const p = prevIndex()
    if (p === -1) return
    playAt(p)
  }

  function handleTrackEnded() {
    if (playMode.value === 'single') {
      // 单曲循环：重新播放当前曲目
      const track = currentTrack.value
      if (track) {
        void requestPlayTrack(track)
        return
      }
    }
    next()
  }

  function cyclePlayMode() {
    const idx = PLAY_MODES.indexOf(playMode.value)
    playMode.value = PLAY_MODES[(idx + 1) % PLAY_MODES.length]
  }

  function setPlayMode(mode: PlayMode) {
    playMode.value = mode
  }

  function togglePlayPause() {
    if (status.value === 'playing') {
      pause()
    } else if (status.value === 'paused') {
      resume()
    } else if (currentTrack.value) {
      // 已停止但队列有曲目：重新播放当前曲目
      void requestPlayTrack(currentTrack.value)
    }
  }

  function pause() {
    streamingAudioPlayer.pause()
    status.value = 'paused'
  }

  function resume() {
    streamingAudioPlayer.resume()
    status.value = 'playing'
  }

  function stop() {
    wsClient.stop()
    streamingAudioPlayer.stop()
    stopStatsPolling()
    streamStats.value = null
    status.value = 'idle'
    currentTime.value = 0
    videoInfo.value = null
    duration.value = 0
    downloadProgress.value = null
    statusMessage.value = ''
  }

  function seek(timeSeconds: number) {
    streamingAudioPlayer.seek(timeSeconds)
    currentTime.value = timeSeconds
  }

  function setVolume(value: number) {
    volume.value = value
    streamingAudioPlayer.setVolume(value)
  }

  function toggleMute() {
    isMuted.value = streamingAudioPlayer.toggleMute()
  }

  /** 把文件名里的非法字符替换成下划线 */
  function sanitizeFilename(name: string): string {
    return name.replace(/[\\/:*?"<>|]/g, '_').slice(0, 100).trim() || 'audio'
  }

  /**
   * 下载当前曲目的音频。按当前 Track 的 bvid/cid 解析代理流，
   * 不依赖这首歌是否已经播放过。
   */
  async function downloadCurrent() {
    const track = currentTrack.value
    const info = videoInfo.value
    const fallbackTrack = track ?? (info ? videoInfoToTrack(info) : null)
    if (!fallbackTrack) {
      setError('没有可下载的曲目')
      return
    }
    if (isDownloading.value) return

    isDownloading.value = true
    statusMessage.value = '正在下载音频...'
    try {
      const playableTrack = await resolvePlayableTrack(fallbackTrack)
      const streamInfo = await getTrackStreamInfo(playableTrack.bvid, playableTrack.cid)
      const response = await fetch(apiUrl(streamInfo.url))
      if (!response.ok) {
        throw new Error(`下载失败（${response.status}）`)
      }
      const blob = await response.blob()
      // 从响应头推断扩展名，默认 .m4a（B站音频流通常是 m4a/aac）
      const contentType = response.headers.get('Content-Type') ?? ''
      const ext = contentType.includes('mp4') || contentType.includes('m4a')
        ? 'm4a'
        : contentType.includes('mpeg')
          ? 'mp3'
          : 'm4a'

      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${sanitizeFilename(playableTrack.title)}.${ext}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      statusMessage.value = '下载完成'
    } catch (error) {
      setError(error instanceof Error ? error.message : '下载失败')
    } finally {
      isDownloading.value = false
    }
  }

  async function resolvePlayableTrack(track: Track): Promise<Track> {
    if (track.cid != null) return track
    const detail = await getTrackDetail(track.bvid)
    const page = detail.pages[0] ?? detail.track
    return { ...track, ...page }
  }

  function syncQueueCurrentTrack(track: Track) {
    const idx = currentIndex.value >= 0 ? currentIndex.value : findTrackIndex(track)
    if (idx >= 0 && idx < queue.value.length) {
      queue.value[idx] = { ...queue.value[idx], ...track }
      currentIndex.value = idx
    } else {
      queue.value.push(track)
      currentIndex.value = queue.value.length - 1
    }
  }

  function findTrackIndex(track: Track): number {
    return queue.value.findIndex((candidate) => isSameTrack(candidate, track))
  }

  function isSameTrack(a: Track, b: Track): boolean {
    if (a.trackId && b.trackId) return a.trackId === b.trackId
    if (a.cid != null && b.cid != null) return a.bvid === b.bvid && a.cid === b.cid
    return a.bvid === b.bvid
  }

  function trackToVideoInfo(track: Track): VideoInfo {
    return {
      trackId: track.trackId,
      bvid: track.bvid,
      cid: track.cid,
      title: track.title,
      duration: track.duration,
      owner: track.owner,
      cover: track.cover,
      playCount: track.playCount,
      publishedAt: track.publishedAt,
    }
  }

  function videoInfoToTrack(info: VideoInfo): Track {
    return {
      trackId: info.trackId,
      bvid: info.bvid,
      cid: info.cid,
      title: info.title,
      duration: info.duration,
      owner: info.owner,
      cover: info.cover,
      playCount: info.playCount,
      publishedAt: info.publishedAt,
    }
  }

  function disconnect() {
    wsClient.disconnect()
    streamingAudioPlayer.destroy()
    isInitialized.value = false
    isConnected.value = false
    status.value = 'idle'
  }

  return {
    status,
    currentTime,
    duration,
    volume,
    isMuted,
    bufferLevel,
    videoInfo,
    errorMessage,
    statusMessage,
    downloadProgress,
    isConnected,
    isInitialized,
    streamStats,
    queue,
    currentIndex,
    playMode,
    currentTrack,
    formattedCurrentTime,
    formattedDuration,
    progress,
    bufferPercent,
    isPlaying,
    isPaused,
    isLoading,
    hasError,
    hasTrack,
    formattedStreamStats,
    initialize,
    playInput,
    playTrack,
    playList,
    enqueue,
    playAt,
    removeFromQueue,
    clearQueue,
    next,
    prev,
    cyclePlayMode,
    setPlayMode,
    togglePlayPause,
    pause,
    resume,
    stop,
    seek,
    setVolume,
    toggleMute,
    clearError,
    disconnect,
    isDownloading,
    downloadCurrent,
  }
})
