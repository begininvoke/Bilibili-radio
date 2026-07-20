import type { AudioStreamInfo, Playlist, Track } from '@/types'

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

export function apiUrl(path: string): string {
  if (/^https?:\/\//.test(path)) return path
  return `${API_BASE_URL}${path}`
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
