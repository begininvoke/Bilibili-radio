import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { Track, Playlist } from '@/types'

const RECENT_KEY = 'bili-radio:recent'
const LIKES_KEY = 'bili-radio:likes'
const PLAYLISTS_KEY = 'bili-radio:playlists'

const RECENT_LIMIT = 100

function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

export const useLibraryStore = defineStore('library', () => {
  const recent = ref<Track[]>(load(RECENT_KEY, []))
  const likes = ref<Track[]>(load(LIKES_KEY, []))
  const playlists = ref<Playlist[]>(load(PLAYLISTS_KEY, []))

  watch(recent, (v) => localStorage.setItem(RECENT_KEY, JSON.stringify(v)), { deep: true })
  watch(likes, (v) => localStorage.setItem(LIKES_KEY, JSON.stringify(v)), { deep: true })
  watch(playlists, (v) => localStorage.setItem(PLAYLISTS_KEY, JSON.stringify(v)), { deep: true })

  function addRecent(track: Track) {
    recent.value = [track, ...recent.value.filter((t) => t.bvid !== track.bvid)].slice(0, RECENT_LIMIT)
  }

  function clearRecent() {
    recent.value = []
  }

  function isLiked(bvid: string): boolean {
    return likes.value.some((t) => t.bvid === bvid)
  }

  function toggleLike(track: Track) {
    if (isLiked(track.bvid)) {
      likes.value = likes.value.filter((t) => t.bvid !== track.bvid)
    } else {
      likes.value = [track, ...likes.value]
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
    return playlist
  }

  function removePlaylist(id: string) {
    playlists.value = playlists.value.filter((p) => p.id !== id)
  }

  function getPlaylist(id: string): Playlist | undefined {
    return playlists.value.find((p) => p.id === id)
  }

  function addToPlaylist(id: string, track: Track) {
    const playlist = playlists.value.find((p) => p.id === id)
    if (!playlist) return
    if (playlist.tracks.some((t) => t.bvid === track.bvid)) return
    playlist.tracks.push(track)
    if (!playlist.cover) playlist.cover = track.cover
  }

  return {
    recent,
    likes,
    playlists,
    addRecent,
    clearRecent,
    isLiked,
    toggleLike,
    createPlaylist,
    removePlaylist,
    getPlaylist,
    addToPlaylist,
  }
})
