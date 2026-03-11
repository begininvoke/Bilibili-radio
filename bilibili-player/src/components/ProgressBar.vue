<template>
  <div class="progress-bar">
    <div class="time-display">{{ formattedCurrentTime }}</div>
    
    <div class="progress-container" @click="handleSeek" ref="progressRef">
      <div class="progress-track">
        <div 
          class="progress-fill" 
          :style="{ width: `${progress}%` }"
        ></div>
        <div 
          class="progress-buffer" 
          :style="{ width: `${bufferPercent}%` }"
        ></div>
      </div>
      <div 
        class="progress-thumb" 
        :style="{ left: `${progress}%` }"
      ></div>
    </div>
    
    <div class="time-display">{{ formattedDuration }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { usePlayerStore } from '@/stores/playerStore'
import { storeToRefs } from 'pinia'

const store = usePlayerStore()
const { formattedCurrentTime, formattedDuration, progress, bufferPercent, duration } = storeToRefs(store)
const { seek } = store

const progressRef = ref<HTMLElement | null>(null)

function handleSeek(event: MouseEvent) {
  if (!progressRef.value || duration.value === 0) return
  
  const rect = progressRef.value.getBoundingClientRect()
  const clickX = event.clientX - rect.left
  const percentage = clickX / rect.width
  const newTime = percentage * duration.value
  
  seek(Math.max(0, Math.min(newTime, duration.value)))
}
</script>

<style scoped>
.progress-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.time-display {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  min-width: 45px;
  text-align: center;
  font-family: 'SF Mono', 'Consolas', monospace;
}

.progress-container {
  flex: 1;
  height: 20px;
  position: relative;
  cursor: pointer;
  display: flex;
  align-items: center;
}

.progress-track {
  width: 100%;
  height: 4px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
  position: relative;
  overflow: hidden;
}

.progress-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: linear-gradient(90deg, #00c7d6, #00e5ff);
  border-radius: 2px;
  transition: width 0.1s ease;
}

.progress-buffer {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.progress-thumb {
  position: absolute;
  width: 12px;
  height: 12px;
  background: #00e5ff;
  border-radius: 50%;
  transform: translateX(-50%);
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.5);
  transition: left 0.1s ease;
  pointer-events: none;
}

.progress-container:hover .progress-track {
  height: 6px;
}

.progress-container:hover .progress-thumb {
  transform: translateX(-50%) scale(1.2);
}
</style>
