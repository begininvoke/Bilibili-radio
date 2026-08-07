<template>
  <main class="lyrics-window" data-tauri-drag-region>
    <div class="lyrics-shell" data-tauri-drag-region>
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
import { onBeforeUnmount, onMounted, reactive } from 'vue'

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
  background: rgba(12, 12, 16, 0.68);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.16);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.34);
}

.lyrics-text {
  width: 100%;
  margin: 0;
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
}

</style>
