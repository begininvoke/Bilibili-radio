<template>
  <div class="status-display">
    <div v-if="statusMessage" class="status-message">
      {{ statusMessage }}
    </div>
    
    <div v-if="errorMessage" class="error-message">
      ⚠️ {{ errorMessage }}
    </div>
    
    <div v-if="downloadProgress && isLoading" class="download-info">
      <span class="speed">{{ formatSpeed(downloadProgress.speed) }}</span>
      <span class="buffer-status">
        缓冲: {{ Math.round(bufferLevel * 100) }}%
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { usePlayerStore } from '@/stores/playerStore'
import { storeToRefs } from 'pinia'

const store = usePlayerStore()
const { statusMessage, errorMessage, downloadProgress, bufferLevel, isLoading } = storeToRefs(store)

function formatSpeed(bytesPerSecond: number): string {
  if (bytesPerSecond < 1024) {
    return `${bytesPerSecond.toFixed(0)} B/s`
  } else if (bytesPerSecond < 1024 * 1024) {
    return `${(bytesPerSecond / 1024).toFixed(1)} KB/s`
  } else {
    return `${(bytesPerSecond / (1024 * 1024)).toFixed(1)} MB/s`
  }
}
</script>

<style scoped>
.status-display {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 24px;
}

.status-message {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

.error-message {
  font-size: 12px;
  color: #ff6b6b;
  background: rgba(255, 107, 107, 0.1);
  padding: 4px 8px;
  border-radius: 4px;
}

.download-info {
  display: flex;
  gap: 16px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

.speed {
  color: #00e5ff;
}

.buffer-status {
  color: rgba(255, 255, 255, 0.6);
}
</style>
