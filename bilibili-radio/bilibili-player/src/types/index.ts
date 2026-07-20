export interface VideoInfo {
  trackId?: string
  bvid: string
  cid?: number | null
  title: string
  duration: number
  owner: string
  cover: string
  playCount?: number
  publishedAt?: string | null
}

export interface AudioStreamInfo {
  url: string
  relativeUrl?: string
  duration: number
  bitrate: number
  sampleRate?: number
  sample_rate: number
  channels: number
  quality?: string
  actualQuality?: string
  codec?: string
  fallback?: boolean
  bvid?: string
  cid?: number
}

/** 播放队列中的一条曲目，也用于最近播放、收藏、歌单 */
export interface Track {
  trackId?: string
  bvid: string
  cid?: number | null
  title: string
  owner: string
  cover: string
  duration: number
  playCount?: number
  publishedAt?: string | null
  page?: number | null
  pageTitle?: string | null
  source?: string
}

export type PlayerStatus = 'idle' | 'loading' | 'playing' | 'paused' | 'error'

/** 播放模式：顺序播放 / 列表循环 / 单曲循环 / 随机 */
export type PlayMode = 'order' | 'loop' | 'single' | 'shuffle'

export interface PlayerState {
  status: PlayerStatus
  currentTime: number
  duration: number
  volume: number
  isMuted: boolean
  bufferLevel: number
  videoInfo: VideoInfo | null
  errorMessage: string | null
}

export interface DownloadProgress {
  downloaded_bytes: number
  total_bytes: number
  speed: number
  state: string
  error: string | null
}

export interface PlaybackProgress {
  current_time: number
  duration: number
  buffer_level: number
  state: string
  error: string | null
}

export interface AudioDataPacket {
  data: string
  sample_rate: number
  channels: number
}

export interface BufferStats {
  size: number
  max_size: number
  fill_ratio: number
  chunk_count: number
  state: string
  total_written: number
  total_read: number
}

/** 本地歌单 */
export interface Playlist {
  id: string
  name: string
  cover: string | null
  tracks: Track[]
  createdAt: number | string
  updatedAt?: string
}
