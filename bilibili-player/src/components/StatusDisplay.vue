<template>
  <div class="status-display">
    <div v-if="statusMessage" class="status-message">
      {{ statusMessage }}
    </div>
    
    <div v-if="errorMessage" class="error-message">
      ⚠️ {{ errorMessage }}
    </div>
    
    <div v-if="formattedStreamStats && isPlaying" class="stream-stats">
      <span class="stat-item">
        📊 流量: {{ formattedStreamStats.sessionMB }} MB
      </span>
      <span class="stat-item speed">
        ⚡ {{ formattedStreamStats.speed }}
      </span>
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
const { statusMessage, errorMessage, downloadProgress, bufferLevel, isLoading, isPlaying, formattedStreamStats } = storeToRefs(store)

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
  color: rgba(232, 121, 249, 0.7);
  text-shadow: 0 0 8px rgba(232, 121, 249, 0.3);
}

.error-message {
  font-size: 12px;
  color: #ff6b9d;
  background: rgba(255, 107, 157, 0.1);
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid rgba(255, 107, 157, 0.2);
}

.stream-stats {
  display: flex;
  gap: 16px;
  font-size: 11px;
  color: rgba(232, 121, 249, 0.7);
  background: rgba(232, 121, 249, 0.05);
  padding: 4px 8px;
  border-radius: 6px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-item.speed {
  color: #e879f9;
  text-shadow: 0 0 8px rgba(232, 121, 249, 0.4);
}

.download-info {
  display: flex;
  gap: 16px;
  font-size: 11px;
  color: rgba(232, 121, 249, 0.5);
}

.speed {
  color: #e879f9;
  text-shadow: 0 0 8px rgba(232, 121, 249, 0.4);
}

.buffer-status {
  color: rgba(232, 121, 249, 0.6);
}
</style>
