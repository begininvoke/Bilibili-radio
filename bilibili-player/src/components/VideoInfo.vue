<template>
  <div class="video-info" v-if="videoInfo">
    <div class="video-title" :title="videoInfo.title">
      {{ videoInfo.title }}
    </div>
    <div class="video-meta">
      <span class="owner">{{ videoInfo.owner }}</span>
      <span class="separator">·</span>
      <span class="bvid">{{ videoInfo.bvid }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { usePlayerStore } from '@/stores/playerStore'
import { storeToRefs } from 'pinia'

const store = usePlayerStore()
const { videoInfo } = storeToRefs(store)
</script>

<style scoped>
.video-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
}

.video-title {
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 280px;
  text-shadow: 0 0 10px rgba(232, 121, 249, 0.3);
}

.video-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: rgba(232, 121, 249, 0.6);
}

.separator {
  color: rgba(232, 121, 249, 0.3);
}

.bvid {
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 11px;
  color: rgba(232, 121, 249, 0.5);
}
</style>
