import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { VideoInfo, PlayerStatus, DownloadProgress, PlaybackProgress, AudioStreamInfo } from '@/types'
import { wsClient } from '@/audio/WsClient'
import { streamingAudioPlayer } from '@/audio/StreamingAudioPlayer'

interface StreamStats {
  total_bytes: number
  session_bytes: number
  elapsed_seconds: number
  bytes_per_second: number
  total_mb: number
  session_mb: number
}

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

  let statsInterval: ReturnType<typeof setInterval> | null = null

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
  const formattedStreamStats = computed(() => {
    if (!streamStats.value) return null
    return {
      sessionMB: streamStats.value.session_mb.toFixed(2),
      totalMB: streamStats.value.total_mb.toFixed(2),
      speed: formatSpeed(streamStats.value.bytes_per_second)
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
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  async function fetchStreamStats() {
    try {
      const response = await fetch('http://localhost:5000/api/stream/stats')
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
      status.value = 'idle'
      currentTime.value = 0
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
      }
    })

    const connected = await wsClient.connect()
    isConnected.value = connected
    
    if (!connected) {
      setError('无法连接到服务器')
      return
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

  function playVideo(input: string) {
    console.log('[playerStore] playVideo called, input:', input)
    if (!input.trim()) {
      setError('请输入BV号或视频链接')
      return
    }

    clearError()
    status.value = 'loading'
    statusMessage.value = '正在获取视频信息...'
    currentTime.value = 0
    
    streamingAudioPlayer.stop()
    console.log('[playerStore] calling wsClient.playVideo')
    wsClient.playVideo(input)
  }

  function togglePlayPause() {
    if (status.value === 'playing') {
      pause()
    } else if (status.value === 'paused') {
      resume()
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
    formattedCurrentTime,
    formattedDuration,
    progress,
    bufferPercent,
    isPlaying,
    isPaused,
    isLoading,
    hasError,
    formattedStreamStats,
    initialize,
    playVideo,
    togglePlayPause,
    pause,
    resume,
    stop,
    seek,
    setVolume,
    toggleMute,
    clearError,
    disconnect
  }
})
