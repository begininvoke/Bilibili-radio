<template>
  <div class="app-container" :class="{ 'window-draggable': isWindowDraggable }">
    <div class="window-header">
      <div class="window-title">
        <span class="title-icon">🎵</span>
        <span class="title-text">B站后台播放器</span>
      </div>
      <div class="connection-status" :class="{ connected: isConnected }">
        {{ isConnected ? '已连接' : '未连接' }}
      </div>
    </div>

    <div class="main-content">
      <UrlInput />
      
      <VideoInfo v-if="videoInfo" />
      
      <ProgressBar />
      
      <div class="controls-row">
        <PlayerControls />
        <VolumeControl />
      </div>
      
      <StatusDisplay />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { usePlayerStore } from '@/stores/playerStore'
import { storeToRefs } from 'pinia'

import UrlInput from '@/components/UrlInput.vue'
import VideoInfo from '@/components/VideoInfo.vue'
import ProgressBar from '@/components/ProgressBar.vue'
import PlayerControls from '@/components/PlayerControls.vue'
import VolumeControl from '@/components/VolumeControl.vue'
import StatusDisplay from '@/components/StatusDisplay.vue'

const store = usePlayerStore()
const { isConnected, videoInfo } = storeToRefs(store)

const isWindowDraggable = ref(false)

onMounted(async () => {
  await store.initialize()
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  background: transparent !important;
  overflow: hidden;
}

#app {
  background: transparent;
}
</style>

<style scoped>
.app-container {
  width: 360px;
  min-height: 200px;
  background: rgba(20, 20, 30, 0.85);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.window-draggable {
  -webkit-app-region: drag;
}

.window-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  -webkit-app-region: drag;
}

.window-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  font-size: 16px;
}

.title-text {
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
}

.connection-status {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 10px;
  background: rgba(255, 107, 107, 0.2);
  color: #ff6b6b;
  transition: all 0.3s ease;
}

.connection-status.connected {
  background: rgba(0, 199, 214, 0.2);
  color: #00e5ff;
}

.main-content {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  -webkit-app-region: no-drag;
}

.controls-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
