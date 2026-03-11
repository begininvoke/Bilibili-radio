<template>
  <div class="volume-control">
    <button 
      class="volume-btn" 
      @click="toggleMute"
      :title="isMuted ? '取消静音' : '静音'"
    >
      <span class="icon">{{ volumeIcon }}</span>
    </button>
    
    <div class="volume-slider-container">
      <input
        type="range"
        min="0"
        max="100"
        :value="volumePercent"
        @input="handleVolumeChange"
        class="volume-slider"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { usePlayerStore } from '@/stores/playerStore'
import { storeToRefs } from 'pinia'

const store = usePlayerStore()
const { volume, isMuted } = storeToRefs(store)
const { setVolume, toggleMute } = store

const volumePercent = computed(() => Math.round(volume.value * 100))

const volumeIcon = computed(() => {
  if (isMuted.value || volume.value === 0) return '🔇'
  if (volume.value < 0.3) return '🔈'
  if (volume.value < 0.7) return '🔉'
  return '🔊'
})

function handleVolumeChange(event: Event) {
  const target = event.target as HTMLInputElement
  setVolume(parseInt(target.value) / 100)
}
</script>

<style scoped>
.volume-control {
  display: flex;
  align-items: center;
  gap: 8px;
}

.volume-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.8);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  transition: color 0.2s ease;
}

.volume-btn:hover {
  color: #fff;
}

.icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.volume-slider-container {
  width: 80px;
}

.volume-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 4px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
  outline: none;
  cursor: pointer;
}

.volume-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 12px;
  height: 12px;
  background: #00e5ff;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 0 6px rgba(0, 229, 255, 0.4);
  transition: transform 0.2s ease;
}

.volume-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.volume-slider::-moz-range-thumb {
  width: 12px;
  height: 12px;
  background: #00e5ff;
  border-radius: 50%;
  cursor: pointer;
  border: none;
  box-shadow: 0 0 6px rgba(0, 229, 255, 0.4);
}
</style>
