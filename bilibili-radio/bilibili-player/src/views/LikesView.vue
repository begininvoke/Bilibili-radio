<template>
  <div class="page">
    <div class="page-head">
      <div class="head-icon">
        <AppIcon name="heart-filled" :size="30" />
      </div>
      <div>
        <span class="kind">我的音乐</span>
        <h1>我喜欢</h1>
        <p class="sub">{{ likes.length }} 首</p>
      </div>
      <button v-if="likes.length" class="primary-btn" @click="playAll">
        <AppIcon name="play" :size="16" />
        <span>播放全部</span>
      </button>
    </div>

    <div v-if="likes.length" class="result-list">
      <TrackRow
        v-for="(t, i) in likes"
        :key="t.trackId ?? `${t.bvid}:${t.cid ?? i}`"
        :track="t"
        :index="i"
        :is-current="isCurrent(t)"
        :is-playing="isPlaying && isCurrent(t)"
        :is-liked="true"
        @play="player.playList(likes, i)"
        @like="library.toggleLike(t)"
        @enqueue="player.enqueue(t)"
      />
    </div>
    <EmptyState
      v-else
      title="还没有喜欢的内容"
      description="点击任意曲目的爱心，就会收藏到这里"
    />
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { usePlayerStore } from '@/stores/playerStore'
import { useLibraryStore } from '@/stores/libraryStore'
import type { Track } from '@/types'
import AppIcon from '@/components/base/AppIcon.vue'
import TrackRow from '@/components/TrackRow.vue'
import EmptyState from '@/components/base/EmptyState.vue'

const player = usePlayerStore()
const library = useLibraryStore()
const { likes } = storeToRefs(library)
const { currentTrack, isPlaying } = storeToRefs(player)

function isCurrent(track: Track): boolean {
  const current = currentTrack.value
  if (!current) return false
  if (current.trackId && track.trackId) return current.trackId === track.trackId
  if (current.cid != null && track.cid != null) return current.bvid === track.bvid && current.cid === track.cid
  return current.bvid === track.bvid
}

function playAll() {
  if (likes.value.length) player.playList(likes.value, 0)
}
</script>

<style scoped>
.page {
  padding: 24px 32px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-head {
  display: flex;
  align-items: center;
  gap: 20px;
}

.head-icon {
  width: 88px;
  height: 88px;
  border-radius: var(--radius-large);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  flex-shrink: 0;
}

.kind {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.page-head h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-top: 2px;
}

.sub {
  margin-top: 4px;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.primary-btn {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
  height: 38px;
  padding: 0 20px;
  border: none;
  border-radius: 19px;
  background: var(--color-primary);
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: background 160ms ease;
}

.primary-btn:hover {
  background: var(--color-primary-hover);
}

.result-list {
  display: flex;
  flex-direction: column;
}
</style>
