import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { VideoInfo, PlayerStatus, DownloadProgress, PlaybackProgress } from '@/types'
import { wsClient } from '@/audio/WsClient'
import { audioPlayer } from '@/audio/AudioPlayer'

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

  function formatTime(seconds: number): string {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  async function initialize() {
    if (isInitialized.value) return

    const playerReady = await audioPlayer.init()
    if (!playerReady) {
      setError('音频播放器初始化失败')
      return
    }

    audioPlayer.onStateChange((playing) => {
      if (playing && status.value !== 'loading') {
        status.value = 'playing'
      }
    })

    audioPlayer.setVolume(volume.value)

    wsClient.setCallbacks({
      onVideoInfo: (info: VideoInfo) => {
        videoInfo.value = info
        duration.value = info.duration
        status.value = 'loading'
        statusMessage.value = '正在加载音频...'
      },
      onAudioData: (data) => {
        audioPlayer.handleAudioData(data)
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
    
    audioPlayer.stopPlayback()
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
    wsClient.pause()
    audioPlayer.pausePlayback()
    status.value = 'paused'
  }

  function resume() {
    wsClient.resume()
    audioPlayer.resumePlayback()
    status.value = 'playing'
  }

  function stop() {
    wsClient.stop()
    audioPlayer.stopPlayback()
    status.value = 'idle'
    currentTime.value = 0
    videoInfo.value = null
    duration.value = 0
    downloadProgress.value = null
    statusMessage.value = ''
  }

  function seek(timeSeconds: number) {
    wsClient.seek(timeSeconds)
    currentTime.value = timeSeconds
  }

  function setVolume(value: number) {
    volume.value = value
    audioPlayer.setVolume(value)
  }

  function toggleMute() {
    isMuted.value = audioPlayer.toggleMute()
  }

  function disconnect() {
    wsClient.disconnect()
    audioPlayer.destroy()
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
    formattedCurrentTime,
    formattedDuration,
    progress,
    bufferPercent,
    isPlaying,
    isPaused,
    isLoading,
    hasError,
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
