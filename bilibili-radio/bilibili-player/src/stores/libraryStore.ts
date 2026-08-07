import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import {
  addLikeTrack,
  addPlaylistItemsRemote,
  addRecentTrack,
  clearRecentTracks,
  createPlaylistRemote,
  deletePlaylistRemote,
  fetchLikes,
  fetchPlaylists,
  fetchRecent,
  removeLikeTrack,
  removeRecentTrack,
} from '@/api/client'
import type { Playlist, Track } from '@/types'

const RECENT_KEY = 'bili-radio:recent'
const LIKES_KEY = 'bili-radio:likes'
const PLAYLISTS_KEY = 'bili-radio:playlists'

const RECENT_LIMIT = 100
const MIGRATION_CONCURRENCY = 4

interface MigrationResult {
  recent: boolean
  likes: boolean
  playlists: boolean
}

function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

async function runWithConcurrency(tasks: Array<() => Promise<unknown>>, limit: number): Promise<void> {
  if (tasks.length === 0) return

  let cursor = 0
  const errors: unknown[] = []
  const workerCount = Math.min(Math.max(1, limit), tasks.length)

  async function worker() {
    while (cursor < tasks.length) {
      const taskIndex = cursor++
      try {
        await tasks[taskIndex]()
      } catch (error) {
        errors.push(error)
      }
    }
  }

  await Promise.all(Array.from({ length: workerCount }, () => worker()))
  if (errors.length > 0) throw errors[0]
}

export const useLibraryStore = defineStore('library', () => {
  const recent = ref<Track[]>(load(RECENT_KEY, []))
  const likes = ref<Track[]>(load(LIKES_KEY, []))
  const playlists = ref<Playlist[]>(load(PLAYLISTS_KEY, []))
  const isSyncing = ref(false)
  const backendAvailable = ref(false)
  const syncError = ref<string | null>(null)

  let initialized = false
  let initializePromise: Promise<void> | null = null

  watch(recent, (v) => localStorage.setItem(RECENT_KEY, JSON.stringify(v)), { deep: true })
  watch(likes, (v) => localStorage.setItem(LIKES_KEY, JSON.stringify(v)), { deep: true })
  watch(playlists, (v) => localStorage.setItem(PLAYLISTS_KEY, JSON.stringify(v)), { deep: true })

  function initialize(): Promise<void> {
    if (initialized) return Promise.resolve()
    if (initializePromise) return initializePromise

    initializePromise = initializeLibrary().finally(() => {
      initializePromise = null
    })
    return initializePromise
  }

  async function initializeLibrary() {

    const localRecent = [...recent.value]
    const localLikes = [...likes.value]
    const localPlaylists = playlists.value.map((playlist) => ({ ...playlist, tracks: [...playlist.tracks] }))

    isSyncing.value = true
    syncError.value = null
    try {
      const [remoteRecent, remoteLikes, remotePlaylists] = await Promise.all([
        fetchRecent(RECENT_LIMIT),
        fetchLikes(),
        fetchPlaylists(),
      ])

      backendAvailable.value = true
      recent.value = mergeTracks(remoteRecent, localRecent).slice(0, RECENT_LIMIT)
      likes.value = mergeTracks(remoteLikes, localLikes)
      playlists.value = mergePlaylists(remotePlaylists, localPlaylists)

      const migrated = await migrateLocalFallback(
        localRecent,
        localLikes,
        localPlaylists,
        remoteRecent,
        remoteLikes,
        remotePlaylists
      )

      const [finalRecent, finalLikes, finalPlaylists] = await Promise.all([
        migrated.recent ? fetchRecent(RECENT_LIMIT) : Promise.resolve(null),
        migrated.likes ? fetchLikes() : Promise.resolve(null),
        migrated.playlists ? fetchPlaylists() : Promise.resolve(null),
      ])
      if (finalRecent !== null) {
        recent.value = finalRecent.length ? finalRecent : recent.value
      }
      if (finalLikes !== null) {
        likes.value = finalLikes.length ? finalLikes : likes.value
      }
      if (finalPlaylists !== null) {
        playlists.value = finalPlaylists.length ? finalPlaylists : playlists.value
      }
      initialized = true
    } catch (error) {
      backendAvailable.value = false
      syncError.value = error instanceof Error ? error.message : '本地库同步失败'
      initialized = true
    } finally {
      isSyncing.value = false
    }
  }

  async function refreshFromBackend() {
    isSyncing.value = true
    syncError.value = null
    try {
      const [remoteRecent, remoteLikes, remotePlaylists] = await Promise.all([
        fetchRecent(RECENT_LIMIT),
        fetchLikes(),
        fetchPlaylists(),
      ])
      backendAvailable.value = true
      recent.value = remoteRecent
      likes.value = remoteLikes
      playlists.value = remotePlaylists
    } catch (error) {
      backendAvailable.value = false
      syncError.value = error instanceof Error ? error.message : '本地库刷新失败'
      throw error
    } finally {
      isSyncing.value = false
    }
  }

  function addRecent(track: Track) {
    const current = recent.value.find((t) => isSameTrack(t, track))
    const nextTrack: Track = {
      ...track,
      recentPlayCount: (current?.recentPlayCount ?? 0) + 1,
    }
    recent.value = [nextTrack, ...recent.value.filter((t) => !isSameTrack(t, track))].slice(0, RECENT_LIMIT)
    if (backendAvailable.value) {
      void addRecentTrack(track).catch(handleBackgroundError)
    }
  }

  function clearRecent() {
    recent.value = []
    if (backendAvailable.value) {
      void clearRecentTracks().catch(handleBackgroundError)
    }
  }

  function removeRecent(track: Track) {
    recent.value = recent.value.filter((item) => !isSameTrack(item, track))
    if (backendAvailable.value) {
      void removeRecentTrack(track).catch(handleBackgroundError)
    }
  }

  function isLiked(bvid: string): boolean {
    return likes.value.some((t) => t.bvid === bvid)
  }

  function isTrackLiked(track: Track): boolean {
    return likes.value.some((t) => isSameTrack(t, track))
  }

  function toggleLike(track: Track) {
    if (isTrackLiked(track)) {
      likes.value = likes.value.filter((t) => !isSameTrack(t, track))
      if (backendAvailable.value) {
        void removeLikeTrack(track).catch(handleBackgroundError)
      }
    } else {
      likes.value = [track, ...likes.value]
      if (backendAvailable.value) {
        void addLikeTrack(track).catch(handleBackgroundError)
      }
    }
  }

  function createPlaylist(name: string, tracks: Track[] = []): Playlist {
    const playlist: Playlist = {
      id: `pl_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      name,
      cover: tracks[0]?.cover ?? null,
      tracks,
      createdAt: Date.now(),
    }
    playlists.value = [playlist, ...playlists.value]

    if (backendAvailable.value) {
      void createPlaylistRemote(name, tracks)
        .then((remote) => {
          playlists.value = playlists.value.map((item) => (item.id === playlist.id ? remote : item))
        })
        .catch(handleBackgroundError)
    }

    return playlist
  }

  function removePlaylist(id: string) {
    playlists.value = playlists.value.filter((p) => p.id !== id)
    if (backendAvailable.value) {
      void deletePlaylistRemote(id).catch(handleBackgroundError)
    }
  }

  function getPlaylist(id: string): Playlist | undefined {
    return playlists.value.find((p) => p.id === id)
  }

  function addToPlaylist(id: string, track: Track) {
    const playlist = playlists.value.find((p) => p.id === id)
    if (!playlist) return
    if (playlist.tracks.some((t) => isSameTrack(t, track))) return
    playlist.tracks.push(track)
    if (!playlist.cover) playlist.cover = track.cover
    if (backendAvailable.value) {
      void addPlaylistItemsRemote(id, [track]).catch(handleBackgroundError)
    }
  }

  function hasPlaylistTrack(id: string, track: Track): boolean {
    const playlist = playlists.value.find((p) => p.id === id)
    return !!playlist && playlist.tracks.some((t) => isSameTrack(t, track))
  }

  async function migrateLocalFallback(
    localRecent: Track[],
    localLikes: Track[],
    localPlaylists: Playlist[],
    remoteRecent: Track[],
    remoteLikes: Track[],
    remotePlaylists: Playlist[]
  ): Promise<MigrationResult> {
    const recentToPush = localRecent.filter((track) => !remoteRecent.some((remote) => isSameTrack(remote, track)))
    const likesToPush = localLikes.filter((track) => !remoteLikes.some((remote) => isSameTrack(remote, track)))
    const playlistNames = new Set(remotePlaylists.map((playlist) => playlist.name))
    const playlistsToPush = localPlaylists.filter((playlist) => !playlistNames.has(playlist.name))

    const tasks: Array<() => Promise<unknown>> = [
      ...recentToPush.map((track) => () => addRecentTrack(track)),
      ...likesToPush.map((track) => () => addLikeTrack(track)),
      ...playlistsToPush.map((playlist) => () => createPlaylistRemote(playlist.name, playlist.tracks)),
    ]
    await runWithConcurrency(tasks, MIGRATION_CONCURRENCY)

    return {
      recent: recentToPush.length > 0,
      likes: likesToPush.length > 0,
      playlists: playlistsToPush.length > 0,
    }
  }

  function mergeTracks(primary: Track[], fallback: Track[]): Track[] {
    const result = [...primary]
    for (const track of fallback) {
      if (!result.some((item) => isSameTrack(item, track))) {
        result.push(track)
      }
    }
    return result
  }

  function mergePlaylists(primary: Playlist[], fallback: Playlist[]): Playlist[] {
    const result = [...primary]
    for (const playlist of fallback) {
      if (!result.some((item) => item.id === playlist.id || item.name === playlist.name)) {
        result.push(playlist)
      }
    }
    return result
  }

  function isSameTrack(a: Track, b: Track): boolean {
    if (a.trackId && b.trackId) return a.trackId === b.trackId
    if (a.cid != null || b.cid != null) return a.bvid === b.bvid && a.cid != null && b.cid != null && a.cid === b.cid
    return a.bvid === b.bvid
  }

  function handleBackgroundError(error: unknown) {
    backendAvailable.value = false
    syncError.value = error instanceof Error ? error.message : '本地库后台同步失败'
  }

  return {
    recent,
    likes,
    playlists,
    isSyncing,
    backendAvailable,
    syncError,
    initialize,
    refreshFromBackend,
    addRecent,
    clearRecent,
    removeRecent,
    isLiked,
    isTrackLiked,
    toggleLike,
    createPlaylist,
    removePlaylist,
    getPlaylist,
    addToPlaylist,
    hasPlaylistTrack,
  }
})
