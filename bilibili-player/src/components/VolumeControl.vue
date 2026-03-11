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
  color: rgba(232, 121, 249, 0.8);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  transition: all 0.2s ease;
  border-radius: 50%;
}

.volume-btn:hover {
  color: #e879f9;
  background: rgba(232, 121, 249, 0.15);
  box-shadow: 0 0 15px rgba(232, 121, 249, 0.3);
}

.icon {
  display: flex;
  align-items: center;
  justify-content: center;
  filter: drop-shadow(0 0 5px rgba(232, 121, 249, 0.5));
}

.volume-slider-container {
  width: 80px;
}

.volume-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 4px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 4px;
  outline: none;
  cursor: pointer;
  box-shadow: inset 0 0 5px rgba(0, 0, 0, 0.3);
}

.volume-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 14px;
  height: 14px;
  background: linear-gradient(135deg, #e879f9, #f0abfc);
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 
    0 0 10px rgba(232, 121, 249, 0.8),
    0 0 20px rgba(168, 85, 247, 0.4);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  border: 2px solid rgba(255, 255, 255, 0.5);
}

.volume-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
  box-shadow: 
    0 0 15px rgba(232, 121, 249, 1),
    0 0 30px rgba(168, 85, 247, 0.6);
}

.volume-slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  background: linear-gradient(135deg, #e879f9, #f0abfc);
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid rgba(255, 255, 255, 0.5);
  box-shadow: 
    0 0 10px rgba(232, 121, 249, 0.8),
    0 0 20px rgba(168, 85, 247, 0.4);
}

.volume-slider::-moz-range-track {
  background: rgba(255, 255, 255, 0.15);
  height: 4px;
  border-radius: 4px;
}
</style>
