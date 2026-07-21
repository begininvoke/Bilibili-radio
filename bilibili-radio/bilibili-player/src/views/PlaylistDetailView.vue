<template>
  <div class="page">
    <template v-if="playlist">
      <div class="detail-top">
        <div class="detail-cover">
          <img v-if="playlist.cover" :src="mediaUrl(playlist.cover)" :alt="playlist.name" />
          <div v-else class="cover-fallback">
            <AppIcon name="list" :size="40" />
          </div>
        </div>
        <div class="detail-info">
          <span class="detail-kind">本地歌单</span>
          <h1 class="detail-title">{{ playlist.name }}</h1>
          <p class="detail-meta">{{ playlist.tracks.length }} 首</p>
          <div class="detail-actions">
            <button class="primary-btn" :disabled="!playlist.tracks.length" @click="playAll">
              <AppIcon name="play" :size="16" />
              <span>播放全部</span>
            </button>
            <button class="ghost-btn danger" @click="remove">
              <AppIcon name="trash" :size="16" />
              <span>删除歌单</span>
            </button>
          </div>
        </div>
      </div>

      <div v-if="playlist.tracks.length" class="result-list">
        <TrackRow
          v-for="(t, i) in playlist.tracks"
          :key="t.trackId ?? `${t.bvid}:${t.cid ?? i}`"
          :track="t"
          :index="i"
          :is-current="isCurrent(t)"
          :is-playing="isPlaying && isCurrent(t)"
          :is-liked="library.isLiked(t.bvid)"
          @play="player.playList(playlist.tracks, i)"
          @like="library.toggleLike(t)"
          @enqueue="player.enqueue(t)"
        />
      </div>
      <EmptyState
        v-else
        title="这个歌单还是空的"
        description="从收藏夹导入，或在任意列表点 + 把内容加进来"
      />
    </template>

    <EmptyState v-else title="歌单不存在" description="它可能已被删除">
      <RouterLink to="/" class="empty-link">回到首页</RouterLink>
    </EmptyState>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { storeToRefs } from 'pinia'
import { usePlayerStore } from '@/stores/playerStore'
import { useLibraryStore } from '@/stores/libraryStore'
import { mediaUrl } from '@/api/client'
import type { Track } from '@/types'
import AppIcon from '@/components/base/AppIcon.vue'
import TrackRow from '@/components/TrackRow.vue'
import EmptyState from '@/components/base/EmptyState.vue'

const route = useRoute()
const router = useRouter()
const player = usePlayerStore()
const library = useLibraryStore()
const { currentTrack, isPlaying } = storeToRefs(player)

const playlist = computed(() => library.getPlaylist(route.params.id as string))

function isCurrent(track: Track): boolean {
  const current = currentTrack.value
  if (!current) return false
  if (current.trackId && track.trackId) return current.trackId === track.trackId
  if (current.cid != null && track.cid != null) return current.bvid === track.bvid && current.cid === track.cid
  return current.bvid === track.bvid
}

function playAll() {
  if (playlist.value?.tracks.length) player.playList(playlist.value.tracks, 0)
}

function remove() {
  if (!playlist.value) return
  if (window.confirm(`确定删除歌单「${playlist.value.name}」？`)) {
    library.removePlaylist(playlist.value.id)
    router.push('/')
  }
}
</script>

<style scoped>
.page {
  padding: 24px 32px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.detail-top {
  display: flex;
  gap: 24px;
  align-items: flex-end;
}

.detail-cover {
  width: 180px;
  height: 180px;
  border-radius: var(--radius-large);
  overflow: hidden;
  background: var(--color-bg-hover);
  box-shadow: var(--shadow-popup);
  flex-shrink: 0;
}

.detail-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
}

.detail-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-kind {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.detail-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.detail-meta {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.detail-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.primary-btn,
.ghost-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 38px;
  padding: 0 18px;
  border-radius: 19px;
  font-size: 14px;
  cursor: pointer;
  transition: background 160ms ease, border-color 160ms ease, color 160ms ease;
}

.primary-btn {
  border: none;
  background: var(--color-primary);
  color: #fff;
}

.primary-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ghost-btn {
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text-primary);
}

.ghost-btn.danger:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.result-list {
  display: flex;
  flex-direction: column;
}

.empty-link {
  color: var(--color-primary);
  text-decoration: none;
  font-size: 14px;
}
</style>
