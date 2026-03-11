<template>
  <div class="player-controls">
    <button 
      class="control-btn play-btn" 
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
  border: 2px solid rgba(232, 121, 249, 0.5);
  background: linear-gradient(135deg, rgba(168, 85, 247, 0.3), rgba(255, 105, 180, 0.3));
  backdrop-filter: blur(10px);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  font-size: 18px;
  box-shadow: 
    0 0 15px rgba(168, 85, 247, 0.3),
    0 0 30px rgba(255, 105, 180, 0.15);
}

.control-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(168, 85, 247, 0.5), rgba(255, 105, 180, 0.5));
  transform: scale(1.08);
  box-shadow: 
    0 0 20px rgba(168, 85, 247, 0.5),
    0 0 40px rgba(255, 105, 180, 0.3);
  border-color: rgba(232, 121, 249, 0.8);
}

.control-btn:active:not(:disabled) {
  transform: scale(0.95);
}

.control-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  box-shadow: none;
}

.control-btn.active {
  background: linear-gradient(135deg, rgba(232, 121, 249, 0.6), rgba(255, 105, 180, 0.6));
  border-color: #e879f9;
  box-shadow: 
    0 0 20px rgba(232, 121, 249, 0.6),
    0 0 40px rgba(255, 105, 180, 0.4),
    inset 0 0 15px rgba(255, 255, 255, 0.1);
}

.control-btn.active:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(232, 121, 249, 0.8), rgba(255, 105, 180, 0.8));
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
  text-shadow: 0 0 10px rgba(255, 255, 255, 0.5);
}

.icon.loading {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
