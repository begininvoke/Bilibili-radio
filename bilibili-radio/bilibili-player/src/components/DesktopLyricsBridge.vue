<template>
  <span class="desktop-lyrics-bridge" aria-hidden="true" />
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { usePlayerStore } from '@/stores/playerStore'
import { useUiStore } from '@/stores/uiStore'

const LYRICS_READY_EVENT = 'desktop-lyrics:ready'

interface LyricsPayload {
  enabled: boolean
  text: string
  color: string
  title: string
}

interface LyricsWindowDebug {
  action: string
  requested_enabled?: boolean | null
  status_before?: unknown
  status_after_show?: unknown
  status_after?: unknown
  steps?: unknown[]
}

const player = usePlayerStore()
const ui = useUiStore()
const { currentTrack, videoInfo, desktopLyricText } = storeToRefs(player)

let unlistenReady: (() => void) | null = null
let lastPayloadKey = ''
let publishRetryTimers: number[] = []

const trackKey = computed(() => {
  const track = currentTrack.value
  const info = videoInfo.value
  return `${track?.bvid ?? info?.bvid ?? ''}:${track?.cid ?? info?.cid ?? ''}`
})

const trackTitle = computed(() => currentTrack.value?.title ?? videoInfo.value?.title ?? '')

onMounted(() => {
  if (!isDesktopRuntime()) return
  void bindLyricsWindowEvents()
})

watch(
  () => ui.lyricsOverlayEnabled,
  (enabled, previousEnabled) => {
    if (enabled) {
      void player.loadCurrentSubtitles()
      void showLyricsWindow().then(() => publishLyricsStateWithRetries())
    } else if (previousEnabled === true) {
      void hideLyricsWindow()
    }
  },
  { immediate: true }
)

watch(
  trackKey,
  () => {
    if (!ui.lyricsOverlayEnabled) return
    void player.loadCurrentSubtitles(true).finally(() => {
      void publishLyricsState(true)
    })
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
  clearPublishRetryTimers()
  void hideLyricsWindow()
  unlistenReady?.()
})

async function showLyricsWindow() {
  if (!isDesktopRuntime() || !ui.lyricsOverlayEnabled) return
  const payload = currentLyricsPayload()
  try {
    const { invoke } = await import('@tauri-apps/api/core')
    const debug = await invoke<LyricsWindowDebug>('set_lyrics_window_payload', {
      enabled: payload.enabled,
      text: payload.text,
      color: payload.color,
      title: payload.title,
    })
    console.info('[desktop-lyrics] bridge show', debug)
  } catch (error) {
    console.warn('Failed to show desktop lyrics window:', error)
  }
}

async function hideLyricsWindow() {
  if (!isDesktopRuntime()) return
  clearPublishRetryTimers()
  lastPayloadKey = ''
  try {
    const { invoke } = await import('@tauri-apps/api/core')
    const debug = await invoke<LyricsWindowDebug>('hide_lyrics_window')
    console.info('[desktop-lyrics] bridge hide', debug)
  } catch (error) {
    console.warn('Failed to hide desktop lyrics window:', error)
  }
}

async function publishLyricsState(force = false) {
  if (!isDesktopRuntime() || !ui.lyricsOverlayEnabled) return
  const payload = currentLyricsPayload()
  const payloadKey = JSON.stringify(payload)
  if (!force && payloadKey === lastPayloadKey) return
  lastPayloadKey = payloadKey
  try {
    const { invoke } = await import('@tauri-apps/api/core')
    const debug = await invoke<LyricsWindowDebug>('set_lyrics_window_payload', {
      enabled: payload.enabled,
      text: payload.text,
      color: payload.color,
      title: payload.title,
    })
    console.info('[desktop-lyrics] bridge payload', debug)
  } catch (error) {
    console.warn('Failed to update desktop lyrics window:', error)
  }
}

function publishLyricsStateWithRetries() {
  clearPublishRetryTimers()
  void publishLyricsState(true)
  for (const delay of [120, 360, 900]) {
    const timer = window.setTimeout(() => {
      void publishLyricsState(true)
    }, delay)
    publishRetryTimers.push(timer)
  }
}

function clearPublishRetryTimers() {
  for (const timer of publishRetryTimers) {
    window.clearTimeout(timer)
  }
  publishRetryTimers = []
}

function currentLyricsPayload(): LyricsPayload {
  return {
    enabled: ui.lyricsOverlayEnabled,
    text: desktopLyricText.value || '-',
    color: ui.lyricsOverlayColor,
    title: trackTitle.value,
  }
}

async function bindLyricsWindowEvents() {
  if (unlistenReady) return
  const { listen } = await import('@tauri-apps/api/event')
  if (!unlistenReady) {
    unlistenReady = await listen(LYRICS_READY_EVENT, () => {
      void publishLyricsState(true)
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
