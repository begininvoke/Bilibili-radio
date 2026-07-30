import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type {
  VideoInfo,
  PlayerStatus,
  PlayMode,
  Track,
  PlayerQueueSnapshot,
} from '@/types'
import {
  apiUrl,
  fetchPlayerQueue,
  getTrackCoverInfo,
  getTrackStreamInfo,
  resolveTrackInput,
  savePlayerQueue,
} from '@/api/client'
import { streamingAudioPlayer } from '@/audio/StreamingAudioPlayer'
import { useLibraryStore } from '@/stores/libraryStore'

const PLAY_MODES: PlayMode[] = ['order', 'loop', 'single', 'shuffle']
const QUEUE_STORAGE_KEY = 'bili-radio:player-queue'
const QUEUE_SAVE_DEBOUNCE_MS = 300

function isPlayMode(value: unknown): value is PlayMode {
  return typeof value === 'string' && PLAY_MODES.includes(value as PlayMode)
}

function loadQueueSnapshot(): PlayerQueueSnapshot {
  try {
    const raw = localStorage.getItem(QUEUE_STORAGE_KEY)
    if (!raw) {
      return { queue: [], currentIndex: -1, playMode: 'order', updatedAt: null }
    }
    const parsed = JSON.parse(raw) as Partial<PlayerQueueSnapshot>
    const queue = Array.isArray(parsed.queue) ? parsed.queue.filter(isValidTrack) : []
    return {
      queue,
      currentIndex: clampQueueIndex(Number(parsed.currentIndex ?? -1), queue.length),
      playMode: isPlayMode(parsed.playMode) ? parsed.playMode : 'order',
      updatedAt: parsed.updatedAt ?? null,
    }
  } catch {
    return { queue: [], currentIndex: -1, playMode: 'order', updatedAt: null }
  }
}

function isValidTrack(value: unknown): value is Track {
  const track = value as Track
  return !!track && typeof track.bvid === 'string' && typeof track.title === 'string'
}

function clampQueueIndex(index: number, queueLength: number): number {
  if (queueLength <= 0) return -1
  if (!Number.isFinite(index)) return -1
  return Math.max(-1, Math.min(Math.trunc(index), queueLength - 1))
}

export const usePlayerStore = defineStore('player', () => {
  const initialQueueSnapshot = loadQueueSnapshot()
  const status = ref<PlayerStatus>('idle')
  const currentTime = ref(0)
  const duration = ref(0)
  const volume = ref(0.8)
  const isMuted = ref(false)
  const bufferLevel = ref(0)
  const videoInfo = ref<VideoInfo | null>(null)
  const errorMessage = ref<string | null>(null)
  const statusMessage = ref<string>('')
  const isInitialized = ref(false)
  const isDownloading = ref(false)

  // 播放队列
  const queue = ref<Track[]>(initialQueueSnapshot.queue)
  const currentIndex = ref(initialQueueSnapshot.currentIndex)
  const playMode = ref<PlayMode>(initialQueueSnapshot.playMode)
  const queueBackendAvailable = ref(false)
  const queueSyncError = ref<string | null>(null)

  let playSeq = 0
  let initializePromise: Promise<void> | null = null
  let queueSaveTimer: ReturnType<typeof setTimeout> | null = null
  let queueRestored = false
  let suppressQueueRemoteSync = false

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

  watch(
    [queue, currentIndex, playMode],
    () => {
      const snapshot = currentQueueSnapshot()
      saveQueueSnapshotLocal(snapshot)
      if (queueRestored && queueBackendAvailable.value && !suppressQueueRemoteSync) {
        scheduleQueueRemoteSave(snapshot)
      }
    },
    { deep: true }
  )

  function currentQueueSnapshot(updatedAt = new Date().toISOString()): PlayerQueueSnapshot {
    const queueItems = queue.value.filter(isValidTrack)
    return {
      queue: queueItems,
      currentIndex: clampQueueIndex(currentIndex.value, queueItems.length),
      playMode: isPlayMode(playMode.value) ? playMode.value : 'order',
      updatedAt,
    }
  }

  function saveQueueSnapshotLocal(snapshot: PlayerQueueSnapshot) {
    localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(snapshot))
  }

  function applyQueueSnapshot(snapshot: PlayerQueueSnapshot) {
    suppressQueueRemoteSync = true
    const tracks = Array.isArray(snapshot.queue) ? snapshot.queue.filter(isValidTrack) : []
    queue.value = tracks
    currentIndex.value = clampQueueIndex(snapshot.currentIndex, tracks.length)
    playMode.value = isPlayMode(snapshot.playMode) ? snapshot.playMode : 'order'
    saveQueueSnapshotLocal({
      queue: tracks,
      currentIndex: currentIndex.value,
      playMode: playMode.value,
      updatedAt: snapshot.updatedAt ?? new Date().toISOString(),
    })
    syncRestoredCurrentTrack()
    window.setTimeout(() => {
      suppressQueueRemoteSync = false
    }, 0)
  }

  async function restorePersistedQueue() {
    if (queueRestored) return

    const localSnapshot = currentQueueSnapshot(initialQueueSnapshot.updatedAt ?? new Date().toISOString())
    try {
      const remoteSnapshot = await fetchPlayerQueue()
      queueBackendAvailable.value = true
      queueSyncError.value = null
      if (remoteSnapshot.updatedAt) {
        applyQueueSnapshot(remoteSnapshot)
      } else if (localSnapshot.queue.length > 0) {
        const saved = await savePlayerQueue(localSnapshot)
        applyQueueSnapshot(saved)
      } else {
        applyQueueSnapshot(localSnapshot)
      }
    } catch (error) {
      queueBackendAvailable.value = false
      queueSyncError.value = error instanceof Error ? error.message : '播放队列同步失败'
      applyQueueSnapshot(localSnapshot)
    } finally {
      queueRestored = true
    }
  }

  function scheduleQueueRemoteSave(snapshot = currentQueueSnapshot()) {
    if (queueSaveTimer) {
      clearTimeout(queueSaveTimer)
    }
    queueSaveTimer = setTimeout(() => {
      queueSaveTimer = null
      void persistQueueRemote(snapshot)
    }, QUEUE_SAVE_DEBOUNCE_MS)
  }

  async function persistQueueRemote(snapshot = currentQueueSnapshot()) {
    try {
      const saved = await savePlayerQueue(snapshot)
      queueBackendAvailable.value = true
      queueSyncError.value = null
      saveQueueSnapshotLocal({
        queue: saved.queue,
        currentIndex: saved.currentIndex,
        playMode: saved.playMode,
        updatedAt: saved.updatedAt ?? snapshot.updatedAt,
      })
    } catch (error) {
      queueBackendAvailable.value = false
      queueSyncError.value = error instanceof Error ? error.message : '播放队列同步失败'
    }
  }

  function syncRestoredCurrentTrack() {
    const track = currentTrack.value
    if (!track) {
      videoInfo.value = null
      duration.value = 0
      return
    }
    videoInfo.value = trackToVideoInfo(track)
    duration.value = track.duration
  }

  function formatTime(seconds: number): string {
    if (!Number.isFinite(seconds) || seconds < 0) seconds = 0
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  function initialize(): Promise<void> {
    if (isInitialized.value) return Promise.resolve()
    if (initializePromise) return initializePromise

    initializePromise = initializePlayer().finally(() => {
      initializePromise = null
    })
    return initializePromise
  }

  async function initializePlayer() {
    await restorePersistedQueue()
    if (isInitialized.value) return

    const playerReady = streamingAudioPlayer.init()
    if (!playerReady) {
      setError('音频播放器初始化失败')
      return
    }

    streamingAudioPlayer.onStateChange((playing) => {
      if (playing) {
        status.value = 'playing'
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

    isInitialized.value = true
  }

  function setError(message: string) {
    errorMessage.value = message
    status.value = 'error'
  }

  function clearError() {
    errorMessage.value = null
  }

  async function requestPlayTrack(track: Track) {
    const seq = ++playSeq
    clearError()
    status.value = 'loading'
    statusMessage.value = '正在获取视频信息...'
    currentTime.value = 0
    streamingAudioPlayer.stop()

    await initialize()
    if (!isInitialized.value || seq !== playSeq) return

    try {
      syncQueueCurrentTrack(track)
      videoInfo.value = trackToVideoInfo(track)
      duration.value = track.duration
      statusMessage.value = '正在解析音频流...'

      const streamInfo = await getTrackStreamInfo(track.bvid, track.cid)
      if (seq !== playSeq) return

      const resolvedCid = streamInfo.cid ?? track.cid
      const playableTrack: Track = {
        ...track,
        trackId: resolvedCid !== track.cid ? undefined : track.trackId,
        cid: resolvedCid,
        duration: streamInfo.duration || track.duration,
      }
      syncQueueCurrentTrack(playableTrack)
      videoInfo.value = trackToVideoInfo(playableTrack)
      duration.value = playableTrack.duration

      statusMessage.value = '正在缓冲音频...'
      streamingAudioPlayer.loadStream(streamInfo)
      useLibraryStore().addRecent(playableTrack)
      hydrateTrackCoverInBackground(playableTrack, seq)
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
        syncRestoredCurrentTrack()
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
    playSeq++
    streamingAudioPlayer.stop()
    status.value = 'idle'
    currentTime.value = 0
    videoInfo.value = null
    duration.value = 0
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
      const streamInfo = await getTrackStreamInfo(fallbackTrack.bvid, fallbackTrack.cid)
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
      a.download = `${sanitizeFilename(fallbackTrack.title)}.${ext}`
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

  async function hydrateTrackCover(track: Track): Promise<Track> {
    if (track.cid == null) return track
    try {
      const coverInfo = await getTrackCoverInfo(track.bvid, track.cid)
      return {
        ...track,
        cover: coverInfo.cover || track.cover,
      }
    } catch (error) {
      console.warn('Failed to hydrate track cover:', error)
      return track
    }
  }

  function hydrateTrackCoverInBackground(track: Track, seq: number) {
    void hydrateTrackCover(track).then((hydratedTrack) => {
      if (seq !== playSeq) return
      const activeTrack = currentTrack.value
      if (!activeTrack || !isSameTrack(activeTrack, track)) return
      if (hydratedTrack.cover === activeTrack.cover) return

      const updatedTrack = { ...activeTrack, ...hydratedTrack }
      queue.value[currentIndex.value] = updatedTrack
      videoInfo.value = trackToVideoInfo(updatedTrack)
    })
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
    if (a.cid != null || b.cid != null) return a.bvid === b.bvid && a.cid != null && b.cid != null && a.cid === b.cid
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
    playSeq++
    streamingAudioPlayer.destroy()
    isInitialized.value = false
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
    isInitialized,
    queue,
    currentIndex,
    playMode,
    queueBackendAvailable,
    queueSyncError,
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
