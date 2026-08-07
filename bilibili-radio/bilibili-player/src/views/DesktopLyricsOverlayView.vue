<template>
  <main class="lyrics-window">
    <div class="lyrics-shell" :style="shellStyle" data-tauri-drag-region @mousedown="startWindowDrag">
      <div
        class="drag-border drag-border-top"
        title="拖动桌面歌词"
        data-tauri-drag-region
      />
      <div
        class="drag-border drag-border-right"
        title="拖动桌面歌词"
        data-tauri-drag-region
      />
      <div
        class="drag-border drag-border-bottom"
        title="拖动桌面歌词"
        data-tauri-drag-region
      />
      <div
        class="drag-border drag-border-left"
        title="拖动桌面歌词"
        data-tauri-drag-region
      />
      <p
        class="lyrics-text"
        :style="{ color: state.color }"
        :title="state.title || state.text"
        aria-live="polite"
      >
        {{ state.text || '-' }}
      </p>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive } from 'vue'
import type { CSSProperties } from 'vue'
import { getCurrentWindow } from '@tauri-apps/api/window'

const LYRICS_UPDATE_EVENT = 'desktop-lyrics:update'
const LYRICS_READY_EVENT = 'desktop-lyrics:ready'

interface LyricsPayload {
  enabled: boolean
  text: string
  color: string
  title: string
}

const state = reactive<LyricsPayload>({
  enabled: false,
  text: '-',
  color: '#fb7299',
  title: '',
})

let unlistenUpdate: (() => void) | null = null

const shellStyle = computed<CSSProperties>(
  () =>
    ({
      '--lyrics-color': state.color,
    }) as CSSProperties
)

onMounted(async () => {
  if (!isDesktopRuntime()) return
  const { emit, listen } = await import('@tauri-apps/api/event')
  unlistenUpdate = await listen<LyricsPayload>(LYRICS_UPDATE_EVENT, (event) => {
    applyLyricsPayload(event.payload)
  })
  await syncCurrentPayload()
  await emit(LYRICS_READY_EVENT)
})

onBeforeUnmount(() => {
  unlistenUpdate?.()
})

function isDesktopRuntime(): boolean {
  return window.location.protocol === 'tauri:' || window.location.hostname === 'tauri.localhost'
}

async function syncCurrentPayload() {
  try {
    const { invoke } = await import('@tauri-apps/api/core')
    const payload = await invoke<LyricsPayload>('current_lyrics_window_payload')
    applyLyricsPayload(payload)
  } catch (error) {
    console.warn('Failed to sync desktop lyrics payload:', error)
  }
}

function applyLyricsPayload(payload: LyricsPayload) {
  state.enabled = payload.enabled
  state.text = payload.text || '-'
  state.color = payload.color || '#fb7299'
  state.title = payload.title || ''
}

async function startWindowDrag(event: MouseEvent) {
  if (!isDesktopRuntime() || event.button !== 0) return
  event.preventDefault()
  try {
    await getCurrentWindow().startDragging()
  } catch (error) {
    console.warn('Failed to drag desktop lyrics window:', error)
  }
}
</script>

<style scoped>
:global(html),
:global(body),
:global(#app) {
  width: 100%;
  height: 100%;
  margin: 0;
  background: transparent !important;
  overflow: hidden;
}

.lyrics-window {
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  pointer-events: auto;
  user-select: none;
}

.lyrics-shell {
  position: relative;
  width: calc(100vw - 20px);
  min-height: 66px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 14px 28px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid transparent;
  box-shadow: none;
  pointer-events: auto;
  transition: border-color 120ms ease;
}

.lyrics-shell:hover {
  border-color: var(--lyrics-color, #fb7299);
}

.drag-border {
  position: absolute;
  pointer-events: auto;
  cursor: move;
}

.drag-border-top {
  top: -1px;
  left: -1px;
  right: -1px;
  height: 16px;
}

.drag-border-right {
  top: -1px;
  right: -1px;
  bottom: -1px;
  width: 16px;
}

.drag-border-bottom {
  right: -1px;
  bottom: -1px;
  left: -1px;
  height: 16px;
}

.drag-border-left {
  top: -1px;
  bottom: -1px;
  left: -1px;
  width: 16px;
}

.lyrics-text {
  width: 100%;
  margin: 0;
  padding: 0 22px;
  overflow: hidden;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: clamp(22px, 4.2vw, 34px);
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: 0;
  text-shadow:
    0 2px 1px rgba(0, 0, 0, 0.85),
    0 0 14px rgba(0, 0, 0, 0.42);
  pointer-events: none;
}
</style>
