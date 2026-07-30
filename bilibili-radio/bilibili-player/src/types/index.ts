export interface VideoInfo {
  trackId?: string
  bvid: string
  cid?: number | null
  title: string
  duration: number
  owner: string
  cover: string
  playCount?: number
  recentPlayCount?: number
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
  recentPlayCount?: number
  publishedAt?: string | null
  page?: number | null
  pageTitle?: string | null
  pageCount?: number | null
  isMultipart?: boolean | null
  source?: string
}

export interface BiliUserProfile {
  mid: number
  name: string
  face: string
  level?: number
  vipType?: number
}

export type AppUserRole = 'user' | 'admin'

export interface AppUser {
  id: string
  displayName: string
  role: AppUserRole
}

export interface AppSession {
  authenticated: boolean
  user: AppUser | null
  csrfToken: string | null
  oidcEnabled: boolean
  biliConnected: boolean
}

export interface AuthStatus {
  qrLoginEnabled: boolean
  isLoggedIn: boolean
  user: BiliUserProfile | null
  cookieUpdatedAt?: string | null
}

export interface AuthQrCode {
  qrcodeKey: string
  url: string
  expiresAt: string
  pollIntervalMs: number
}

export interface AuthQrStatus {
  qrcodeKey: string
  status: 'waiting' | 'scanned' | 'confirmed' | 'expired' | 'unknown'
  code: number
  message: string
  isLoggedIn: boolean
  user: BiliUserProfile | null
}

export interface AdminStatsSummary {
  range: string
  generatedAt: string
  monitoringUrl?: string | null
  users: {
    total: number
    active: number
    newUsers: number
    admins: number
  }
  traffic: {
    requests: number | null
    errorRate: number | null
    p95LatencyMs: number | null
  }
  playback: {
    plays: number
    skips: number
    listenSeconds: number
  }
}

export interface AdminUser {
  id: string
  displayName: string
  email?: string | null
  role: AppUserRole
  status: 'active' | 'disabled'
  createdAt: string
  lastLoginAt?: string | null
}

export interface AdminUsersPage {
  items: AdminUser[]
  total: number
  page: number
  pageSize: number
}

export interface AdminRoleToggleResult {
  id: string
  role: AppUserRole
}

export interface FavoriteFolder {
  mediaId: number
  id: number
  fid?: number | null
  mid: number
  title: string
  cover: string
  mediaCount: number
  attr: number
  favoriteState: number
}

export interface TrackCoverInfo {
  bvid: string
  cid?: number | null
  cover: string
  videoCover: string
  pageCover?: string | null
  ownerFace?: string
  pages: Array<{
    cid: number
    page: number
    pageTitle: string
    cover: string
    firstFrame?: string | null
  }>
}

export interface PlayerQueueSnapshot {
  queue: Track[]
  currentIndex: number
  playMode: PlayMode
  updatedAt?: string | null
}

export interface TrackIntro {
  bvid: string
  cid?: number | null
  title: string
  description: string
  dynamic: string
  owner: {
    mid: number
    name: string
    face: string
  }
  publishedAt?: string | null
  stats: {
    view: number
    danmaku: number
    reply: number
    favorite: number
    coin: number
    share: number
    like: number
  }
  pages: Array<{
    cid: number
    page: number
    title: string
    duration: number
  }>
}

export interface TrackSubtitleInfo {
  id: number
  lan: string
  lanDoc: string
  url: string
  authorMid: number
  type: number
}

export interface TrackSubtitleLine {
  from: number
  to: number
  text: string
}

export interface TrackSubtitles {
  bvid: string
  cid: number
  needLogin: boolean
  subtitles: TrackSubtitleInfo[]
  activeSubtitleId?: number | null
  lines: TrackSubtitleLine[]
}

export interface TrackChapter {
  from: number
  to: number
  title: string
  cover: string
}

export interface TrackChapters {
  bvid: string
  cid: number
  chapters: TrackChapter[]
}

export interface TrackComment {
  id: string
  author: {
    mid: number
    name: string
    avatar: string
  }
  message: string
  like: number
  replyCount: number
  createdAt?: string | null
}

export interface TrackComments {
  bvid: string
  aid: number
  page: number
  pageSize: number
  total: number
  hasMore: boolean
  comments: TrackComment[]
}

export interface TrackReview {
  trackId: string
  bvid: string
  cid?: number | null
  rating: number
  mood: string
  note: string
  visibility: 'private'
  createdAt: string
  updatedAt: string
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
