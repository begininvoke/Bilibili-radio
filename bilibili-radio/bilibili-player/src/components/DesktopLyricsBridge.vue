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

let overlayWindow: import('@tauri-apps/api/webviewWindow').WebviewWindow | null = null
let unlistenReady: (() => void) | null = null
let unlistenClose: (() => void) | null = null
let ensurePromise: Promise<import('@tauri-apps/api/webviewWindow').WebviewWindow | null> | null = null

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
  const lyricsWindow = await ensureLyricsWindow()
  if (!lyricsWindow) return
  await lyricsWindow.show()
  await lyricsWindow.setAlwaysOnTop(true)
  await lyricsWindow.setSkipTaskbar(true)
  await publishLyricsState()
}

async function hideLyricsWindow() {
  if (!overlayWindow) return
  await emitLyricsPayload({ ...currentLyricsPayload(), enabled: false })
  await overlayWindow.hide()
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
  await emitTo(LYRICS_WINDOW_LABEL, LYRICS_UPDATE_EVENT, payload)
}

async function ensureLyricsWindow() {
  if (overlayWindow) return overlayWindow
  if (ensurePromise) return ensurePromise

  ensurePromise = createOrGetLyricsWindow().finally(() => {
    ensurePromise = null
  })
  return ensurePromise
}

async function createOrGetLyricsWindow() {
  const { WebviewWindow } = await import('@tauri-apps/api/webviewWindow')
  const { listen } = await import('@tauri-apps/api/event')
  const existing = await WebviewWindow.getByLabel(LYRICS_WINDOW_LABEL)
  overlayWindow = existing ?? new WebviewWindow(LYRICS_WINDOW_LABEL, {
    url: '/#/desktop-lyrics',
    title: 'Bilibili Radio Lyrics',
    width: 920,
    height: 112,
    minWidth: 520,
    minHeight: 76,
    decorations: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: true,
    visible: false,
    focus: false,
  })

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

  return overlayWindow
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
