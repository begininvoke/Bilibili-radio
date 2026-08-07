<template>
  <span class="desktop-lyrics-bridge" aria-hidden="true" />
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { usePlayerStore } from '@/stores/playerStore'
import { useUiStore } from '@/stores/uiStore'

const LYRICS_WINDOW_LABEL = 'desktop-lyrics'
const LYRICS_UPDATE_EVENT = 'desktop-lyrics:update'
const LYRICS_READY_EVENT = 'desktop-lyrics:ready'
const LYRICS_CLOSE_EVENT = 'desktop-lyrics:close-requested'

interface LyricsPayload {
  enabled: boolean
  text: string
  color: string
  title: string
}

const player = usePlayerStore()
const ui = useUiStore()
const { currentTrack, videoInfo, desktopLyricText } = storeToRefs(player)

let unlistenReady: (() => void) | null = null
let unlistenClose: (() => void) | null = null
let listenersPromise: Promise<void> | null = null

const trackKey = computed(() => {
  const track = currentTrack.value
  const info = videoInfo.value
  return `${track?.bvid ?? info?.bvid ?? ''}:${track?.cid ?? info?.cid ?? ''}`
})

const trackTitle = computed(() => currentTrack.value?.title ?? videoInfo.value?.title ?? '')

watch(
  () => ui.lyricsOverlayEnabled,
  (enabled) => {
    if (enabled) {
      void player.loadCurrentSubtitles()
      void showLyricsWindow()
    } else {
      void hideLyricsWindow()
    }
  },
  { immediate: true }
)

watch(
  trackKey,
  () => {
    if (!ui.lyricsOverlayEnabled) return
    void player.loadCurrentSubtitles(true)
    void publishLyricsState()
  }
)

watch(
  [desktopLyricText, () => ui.lyricsOverlayColor, trackTitle],
  () => {
    if (!ui.lyricsOverlayEnabled) return
    void publishLyricsState()
  }
)

onBeforeUnmount(() => {
  void hideLyricsWindow()
  unlistenReady?.()
  unlistenClose?.()
})

async function showLyricsWindow() {
  if (!isDesktopRuntime()) return
  try {
    await ensureLyricsListeners()
    const { invoke } = await import('@tauri-apps/api/core')
    await invoke('desktop_show_lyrics_window')
    await publishLyricsState()
    player.statusMessage = '悬浮字幕已打开'
  } catch (error) {
    ui.setLyricsOverlayEnabled(false)
    player.statusMessage = error instanceof Error ? error.message : '悬浮字幕打开失败'
  }
}

async function hideLyricsWindow() {
  if (!isDesktopRuntime()) return
  try {
    await emitLyricsPayload({ ...currentLyricsPayload(), enabled: false })
    const { invoke } = await import('@tauri-apps/api/core')
    await invoke('desktop_hide_lyrics_window')
  } catch {
    // The overlay may already be closed by the OS; the UI switch is the source of truth.
  }
}

async function publishLyricsState() {
  await emitLyricsPayload(currentLyricsPayload())
}

function currentLyricsPayload(): LyricsPayload {
  return {
    enabled: ui.lyricsOverlayEnabled,
    text: desktopLyricText.value || '-',
    color: ui.lyricsOverlayColor,
    title: trackTitle.value,
  }
}

async function emitLyricsPayload(payload: LyricsPayload) {
  if (!isDesktopRuntime()) return
  const { emitTo } = await import('@tauri-apps/api/event')
  await emitTo(LYRICS_WINDOW_LABEL, LYRICS_UPDATE_EVENT, payload).catch(() => undefined)
}

async function ensureLyricsListeners() {
  if (unlistenReady && unlistenClose) return
  if (listenersPromise) return listenersPromise

  listenersPromise = registerLyricsListeners().finally(() => {
    listenersPromise = null
  })
  return listenersPromise
}

async function registerLyricsListeners() {
  const { listen } = await import('@tauri-apps/api/event')

  if (!unlistenReady) {
    unlistenReady = await listen(LYRICS_READY_EVENT, () => {
      void publishLyricsState()
    })
  }
  if (!unlistenClose) {
    unlistenClose = await listen(LYRICS_CLOSE_EVENT, () => {
      ui.setLyricsOverlayEnabled(false)
    })
  }
}

function isDesktopRuntime(): boolean {
  return window.location.protocol === 'tauri:' || window.location.hostname === 'tauri.localhost'
}
</script>

<style scoped>
.desktop-lyrics-bridge {
  display: none;
}
</style>
