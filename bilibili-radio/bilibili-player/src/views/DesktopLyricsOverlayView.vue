<template>
  <main class="lyrics-window" :class="{ disabled: !state.enabled }" data-tauri-drag-region>
    <div class="lyrics-shell" data-tauri-drag-region>
      <p class="lyrics-text" :style="{ color: state.color }" :title="state.title || state.text">
        {{ state.text || '-' }}
      </p>
      <button class="close-btn" type="button" title="关闭悬浮字幕" @click="requestClose">×</button>
    </div>
  </main>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive } from 'vue'

const LYRICS_UPDATE_EVENT = 'desktop-lyrics:update'
const LYRICS_READY_EVENT = 'desktop-lyrics:ready'
const LYRICS_CLOSE_EVENT = 'desktop-lyrics:close-requested'

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
    state.enabled = event.payload.enabled
    state.text = event.payload.text || '-'
    state.color = event.payload.color || '#fb7299'
    state.title = event.payload.title || ''
  })
  await emit(LYRICS_READY_EVENT)
})

onBeforeUnmount(() => {
  unlistenUpdate?.()
})

async function requestClose() {
  if (!isDesktopRuntime()) return
  const { emit } = await import('@tauri-apps/api/event')
  await emit(LYRICS_CLOSE_EVENT)
}

function isDesktopRuntime(): boolean {
  return window.location.protocol === 'tauri:' || window.location.hostname === 'tauri.localhost'
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

.lyrics-window.disabled {
  display: none;
}

.lyrics-shell {
  position: relative;
  width: calc(100vw - 20px);
  min-height: 66px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 14px 56px;
  border-radius: 8px;
  background: rgba(12, 12, 16, 0.24);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
  box-shadow: 0 10px 26px rgba(0, 0, 0, 0.22);
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

.close-btn {
  position: absolute;
  right: 12px;
  top: 50%;
  width: 30px;
  height: 30px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.28);
  color: rgba(255, 255, 255, 0.72);
  font-size: 20px;
  line-height: 1;
  opacity: 0;
  cursor: pointer;
  transition: opacity 140ms ease, background 140ms ease, color 140ms ease;
}

.lyrics-shell:hover .close-btn {
  opacity: 1;
}

.close-btn:hover {
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
}
</style>
