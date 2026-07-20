<template>
  <div
    class="track-row"
    :class="{ active: isCurrent }"
    @dblclick="$emit('play')"
  >
    <div class="col-index">
      <PlayingBars v-if="isCurrent && isPlaying" />
      <span v-else class="index-num">{{ index + 1 }}</span>
      <button class="row-play" :title="'播放'" @click.stop="$emit('play')">
        <AppIcon name="play" :size="16" />
      </button>
    </div>

    <img class="col-cover" :src="track.cover" :alt="track.title" loading="lazy" />

    <div class="col-main">
      <div class="row-title" :class="{ 'is-current': isCurrent }" :title="track.title">
        {{ track.title }}
      </div>
      <div class="row-owner">{{ track.owner }}</div>
    </div>

    <div class="col-duration">{{ formatDuration(track.duration) }}</div>

    <div class="col-actions">
      <button
        class="action-btn"
        :class="{ liked: isLiked }"
        :title="isLiked ? '取消喜欢' : '喜欢'"
        @click.stop="$emit('like')"
      >
        <AppIcon :name="isLiked ? 'heart-filled' : 'heart'" :size="16" />
      </button>
      <button class="action-btn" title="添加到队列" @click.stop="$emit('enqueue')">
        <AppIcon name="plus" :size="16" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Track } from '@/types'
import { formatDuration } from '@/utils/format'
import AppIcon from '@/components/base/AppIcon.vue'
import PlayingBars from '@/components/base/PlayingBars.vue'

defineProps<{
  track: Track
  index: number
  isCurrent?: boolean
  isPlaying?: boolean
  isLiked?: boolean
}>()

defineEmits<{
  play: []
  like: []
  enqueue: []
}>()
</script>

<style scoped>
.track-row {
  display: grid;
  grid-template-columns: 40px 44px 1fr auto auto;
  align-items: center;
  gap: 16px;
  height: 64px;
  padding: 0 12px;
  border-radius: var(--radius-small);
  cursor: default;
  transition: background 160ms ease;
  user-select: none;
}

.track-row:hover {
  background: var(--color-bg-hover);
}

.track-row.active {
  background: var(--color-primary-soft);
}

.col-index {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--color-text-tertiary);
}

.index-num {
  font-variant-numeric: tabular-nums;
}

.row-play {
  position: absolute;
  inset: 0;
  display: none;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--color-primary);
  cursor: pointer;
}

.track-row:hover .index-num {
  opacity: 0;
}

.track-row:hover .row-play {
  display: flex;
}

.col-cover {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-small);
  object-fit: cover;
  background: var(--color-bg-hover);
}

.col-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.row-title {
  font-size: 14px;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.row-title.is-current {
  color: var(--color-primary);
}

.row-owner {
  font-size: 12px;
  color: var(--color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.col-duration {
  font-size: 13px;
  color: var(--color-text-tertiary);
  font-variant-numeric: tabular-nums;
  min-width: 44px;
  text-align: right;
}

.col-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 160ms ease;
}

.track-row:hover .col-actions {
  opacity: 1;
}

.action-btn {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: 50%;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background 160ms ease, color 160ms ease;
}

.action-btn:hover {
  background: rgba(0, 0, 0, 0.06);
  color: var(--color-text-primary);
}

[data-theme='dark'] .action-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.action-btn.liked {
  color: var(--color-primary);
  opacity: 1;
}

/* 喜欢按钮在未 hover 行时也保持可见（若已喜欢） */
.track-row .col-actions:has(.liked) {
  opacity: 1;
}
</style>
