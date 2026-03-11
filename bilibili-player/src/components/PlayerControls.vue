<template>
  <div class="player-controls">
    <button 
      class="control-btn" 
      :class="{ active: isPlaying }"
      @click="togglePlayPause"
      :disabled="isLoading || hasError || !videoInfo"
      :title="isPlaying ? '暂停' : '播放'"
    >
      <span v-if="isLoading" class="icon loading">⟳</span>
      <span v-else-if="isPlaying" class="icon">⏸</span>
      <span v-else class="icon">▶</span>
    </button>
    
    <button 
      class="control-btn stop-btn" 
      @click="stop"
      :disabled="!videoInfo"
      title="停止"
    >
      <span class="icon">⏹</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { usePlayerStore } from '@/stores/playerStore'
import { storeToRefs } from 'pinia'

const store = usePlayerStore()
const { isPlaying, isLoading, hasError, videoInfo } = storeToRefs(store)
const { togglePlayPause, stop } = store
</script>

<style scoped>
.player-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.control-btn {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  font-size: 18px;
}

.control-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.25);
  transform: scale(1.05);
}

.control-btn:active:not(:disabled) {
  transform: scale(0.95);
}

.control-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.control-btn.active {
  background: rgba(0, 199, 214, 0.4);
}

.control-btn.active:hover:not(:disabled) {
  background: rgba(0, 199, 214, 0.6);
}

.stop-btn {
  width: 40px;
  height: 40px;
  font-size: 14px;
}

.icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon.loading {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
