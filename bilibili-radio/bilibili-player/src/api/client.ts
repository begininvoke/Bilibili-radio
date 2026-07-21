import type {
  AudioStreamInfo,
  AuthQrCode,
  AuthQrStatus,
  AuthStatus,
  FavoriteFolder,
  PlayerQueueSnapshot,
  Playlist,
  Track,
  TrackChapters,
  TrackComments,
  TrackCoverInfo,
  TrackIntro,
  TrackSubtitles,
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'

interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: {
    code: string
    message: string
  }
}

export interface SearchTracksResult {
  keyword: string
  page: number
  pageSize: number
  tracks: Track[]
}

export interface TrackDetailResult {
  track: Track
  pages: Track[]
}

export interface TrackStreamInfo extends AudioStreamInfo {
  relativeUrl?: string
  bvid?: string
  cid?: number
  quality?: string
  actualQuality?: string
  codec?: string
  fallback?: boolean
}

export interface TrackListResult {
  tracks: Track[]
}

export interface PlaylistListResult {
  playlists: Playlist[]
}

export interface FavoriteFolderListResult {
  folders: FavoriteFolder[]
}

export interface FavoriteTracksResult {
  mediaId: number
  page: number
  pageSize: number
  hasMore: boolean
  total: number
  unavailable: number
  folder: FavoriteFolder
  tracks: Track[]
}

export interface FavoriteImportResult {
  playlist?: Playlist
  import: {
    total: number
    added: number
    duplicated: number
    unavailable: number
    write: boolean
  }
  favorite: {
    mediaId: number
    folder: FavoriteFolder
    fetched: number
    unavailable: number
    hasMore: boolean
    pagesFetched: number[]
    pageSize: number
    maxPages: number
  }
}

export function apiUrl(path: string): string {
  if (/^https?:\/\//.test(path)) return path
  return `${API_BASE_URL}${path}`
}

export function mediaUrl(url?: string | null): string {
  const value = (url || '').trim()
  if (!value) return ''
  if (value.startsWith('data:') || value.startsWith('blob:')) return value
  if (value.startsWith('/') && !value.startsWith('//')) return value
  if (!/^https?:\/\//.test(value)) return value
  return apiUrl(`/api/images/proxy?url=${encodeURIComponent(value)}`)
}

export class ApiError extends Error {
  readonly code: string
  readonly status: number

  constructor(message: string, code = 'UNKNOWN_ERROR', status = 0) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

export async function searchTracks(keyword: string, page = 1, pageSize = 20): Promise<SearchTracksResult> {
  const params = new URLSearchParams({
    keyword,
    page: String(page),
    page_size: String(pageSize),
  })

  return apiRequest<SearchTracksResult>(`/api/search?${params.toString()}`)
}

export async function resolveTrackInput(input: string): Promise<TrackDetailResult> {
  const params = new URLSearchParams({ input })
  return apiRequest<TrackDetailResult>(`/api/tracks/resolve?${params.toString()}`)
}

export async function getTrackDetail(bvid: string): Promise<TrackDetailResult> {
  return apiRequest<TrackDetailResult>(`/api/tracks/${encodeURIComponent(bvid)}`)
}

export async function getTrackCoverInfo(bvid: string, cid?: number | null): Promise<TrackCoverInfo> {
  const safeBvid = encodeURIComponent(bvid)
  if (cid != null) {
    return apiRequest<TrackCoverInfo>(`/api/tracks/${safeBvid}/${cid}/cover`)
  }
  return apiRequest<TrackCoverInfo>(`/api/tracks/${safeBvid}/cover`)
}

export async function getTrackIntro(bvid: string, cid?: number | null): Promise<TrackIntro> {
  return apiRequest<TrackIntro>(trackScopedPath(bvid, cid, 'intro'))
}

export async function getTrackSubtitles(bvid: string, cid?: number | null): Promise<TrackSubtitles> {
  return apiRequest<TrackSubtitles>(trackScopedPath(bvid, cid, 'subtitles'))
}

export async function getTrackChapters(bvid: string, cid?: number | null): Promise<TrackChapters> {
  return apiRequest<TrackChapters>(trackScopedPath(bvid, cid, 'chapters'))
}

export async function getTrackComments(
  bvid: string,
  cid?: number | null,
  page = 1,
  pageSize = 20
): Promise<TrackComments> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  return apiRequest<TrackComments>(`${trackScopedPath(bvid, cid, 'comments')}?${params.toString()}`)
}

export async function getTrackStreamInfo(
  bvid: string,
  cid?: number | null,
  quality = 'auto'
): Promise<TrackStreamInfo> {
  const params = new URLSearchParams({ quality })
  const safeBvid = encodeURIComponent(bvid)
  if (cid != null) {
    return apiRequest<TrackStreamInfo>(`/api/tracks/${safeBvid}/${cid}/stream-info?${params.toString()}`)
  }
  return apiRequest<TrackStreamInfo>(`/api/tracks/${safeBvid}/stream-info?${params.toString()}`)
}

export async function resetStreamStats(): Promise<void> {
  await apiRequest('/api/stream/stats/reset', { method: 'POST' })
}

export async function fetchPlayerQueue(): Promise<PlayerQueueSnapshot> {
  return apiRequest<PlayerQueueSnapshot>('/api/player/queue')
}

export async function savePlayerQueue(snapshot: PlayerQueueSnapshot): Promise<PlayerQueueSnapshot> {
  return apiRequest<PlayerQueueSnapshot>('/api/player/queue', {
    method: 'PUT',
    body: JSON.stringify({
      queue: snapshot.queue,
      currentIndex: snapshot.currentIndex,
      playMode: snapshot.playMode,
    }),
    headers: { 'Content-Type': 'application/json' },
  })
}

export async function clearPlayerQueueRemote(): Promise<PlayerQueueSnapshot> {
  return apiRequest<PlayerQueueSnapshot>('/api/player/queue', { method: 'DELETE' })
}

export async function fetchRecent(limit = 100): Promise<Track[]> {
  const params = new URLSearchParams({ limit: String(limit) })
  const data = await apiRequest<TrackListResult>(`/api/library/recent?${params.toString()}`)
  return data.tracks
}

export async function addRecentTrack(track: Track): Promise<void> {
  await apiRequest('/api/library/recent', {
    method: 'POST',
    body: JSON.stringify({ track }),
    headers: { 'Content-Type': 'application/json' },
  })
}

export async function clearRecentTracks(): Promise<void> {
  await apiRequest('/api/library/recent', { method: 'DELETE' })
}

export async function fetchLikes(): Promise<Track[]> {
  const data = await apiRequest<TrackListResult>('/api/library/likes')
  return data.tracks
}

export async function addLikeTrack(track: Track): Promise<void> {
  await apiRequest(`/api/library/likes/${encodeURIComponent(track.bvid)}`, {
    method: 'POST',
    body: JSON.stringify({ track }),
    headers: { 'Content-Type': 'application/json' },
  })
}

export async function removeLikeTrack(track: Track): Promise<void> {
  const params = new URLSearchParams()
  if (track.cid != null) params.set('cid', String(track.cid))
  const query = params.toString()
  await apiRequest(`/api/library/likes/${encodeURIComponent(track.bvid)}${query ? `?${query}` : ''}`, {
    method: 'DELETE',
  })
}

export async function fetchPlaylists(): Promise<Playlist[]> {
  const data = await apiRequest<PlaylistListResult>('/api/library/playlists')
  return data.playlists
}

export async function createPlaylistRemote(name: string, tracks: Track[] = []): Promise<Playlist> {
  return apiRequest<Playlist>('/api/library/playlists', {
    method: 'POST',
    body: JSON.stringify({ name, tracks }),
    headers: { 'Content-Type': 'application/json' },
  })
}

export async function deletePlaylistRemote(id: string): Promise<void> {
  await apiRequest(`/api/library/playlists/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export async function addPlaylistItemsRemote(id: string, tracks: Track[]): Promise<void> {
  await apiRequest(`/api/library/playlists/${encodeURIComponent(id)}/items:batch`, {
    method: 'POST',
    body: JSON.stringify({ tracks }),
    headers: { 'Content-Type': 'application/json' },
  })
}

export async function fetchAuthStatus(refresh = false): Promise<AuthStatus> {
  const params = new URLSearchParams({ refresh: String(refresh) })
  return apiRequest<AuthStatus>(`/api/auth/status?${params.toString()}`)
}

export async function createBiliLoginQr(): Promise<AuthQrCode> {
  return apiRequest<AuthQrCode>('/api/auth/qrcode')
}

export async function pollBiliLoginQr(qrcodeKey: string): Promise<AuthQrStatus> {
  const params = new URLSearchParams({ qrcodeKey })
  return apiRequest<AuthQrStatus>(`/api/auth/qrcode/status?${params.toString()}`)
}

export async function logoutBili(): Promise<void> {
  await apiRequest('/api/auth/logout', { method: 'POST' })
}

export async function fetchBiliFavoriteFolders(upMid?: number): Promise<FavoriteFolder[]> {
  const params = new URLSearchParams()
  if (upMid != null) params.set('upMid', String(upMid))
  const query = params.toString()
  const data = await apiRequest<FavoriteFolderListResult>(`/api/bili/favorites${query ? `?${query}` : ''}`)
  return data.folders
}

export async function fetchBiliFavoriteTracks(
  mediaId: number,
  page = 1,
  pageSize = 20
): Promise<FavoriteTracksResult> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  return apiRequest<FavoriteTracksResult>(`/api/bili/favorites/${mediaId}/tracks?${params.toString()}`)
}

export async function importBiliFavoriteToPlaylist(
  playlistId: string,
  mediaId: number,
  maxPages = 10,
  pageSize = 20
): Promise<FavoriteImportResult> {
  return apiRequest<FavoriteImportResult>(`/api/library/playlists/${encodeURIComponent(playlistId)}/import/favorite`, {
    method: 'POST',
    body: JSON.stringify({ mediaId, maxPages, pageSize }),
    headers: { 'Content-Type': 'application/json' },
  })
}

export async function importBiliFavoriteAsPlaylist(
  mediaId: number,
  name?: string,
  maxPages = 10,
  pageSize = 20
): Promise<FavoriteImportResult> {
  return apiRequest<FavoriteImportResult>('/api/library/playlists/import/favorite', {
    method: 'POST',
    body: JSON.stringify({ mediaId, name, maxPages, pageSize }),
    headers: { 'Content-Type': 'application/json' },
  })
}

export async function recordAnalysisEvent(event: string, payload: Record<string, unknown> = {}): Promise<void> {
  await apiRequest('/api/analysis/events', {
    method: 'POST',
    body: JSON.stringify({ event, payload }),
    headers: { 'Content-Type': 'application/json' },
  })
}

function trackScopedPath(bvid: string, cid: number | null | undefined, suffix: string): string {
  const safeBvid = encodeURIComponent(bvid)
  if (cid != null) {
    return `/api/tracks/${safeBvid}/${cid}/${suffix}`
  }
  return `/api/tracks/${safeBvid}/${suffix}`
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.headers ?? {}),
    },
  })

  const payload = (await response.json().catch(() => null)) as ApiResponse<T> | null
  if (!response.ok || !payload?.success) {
    const error = payload?.error
    throw new ApiError(
      error?.message || `Request failed with status ${response.status}`,
      error?.code,
      response.status
    )
  }

  return payload.data as T
}
