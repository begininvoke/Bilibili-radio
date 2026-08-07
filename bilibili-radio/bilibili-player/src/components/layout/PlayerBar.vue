<template>
  <div class="player-bar">
    <!-- 左侧 30%：当前内容 -->
    <div class="player-left">
      <template v-if="track">
        <div class="mini-cover" @click="ui.openNowPlaying()">
          <img v-if="track.cover" :src="mediaUrl(track.cover)" :alt="track.title" />
          <div v-else class="cover-fallback">
            <AppIcon name="disc" :size="22" />
          </div>
          <div class="cover-mask">
            <AppIcon name="chevron" :size="18" class="expand-icon" />
          </div>
        </div>
        <div class="track-meta">
          <div class="meta-title" :title="track.title">{{ track.title }}</div>
          <div class="meta-owner" :title="track.owner">{{ track.owner }}</div>
        </div>
        <button
          class="icon-btn like-btn"
          :class="{ liked: isLiked }"
          :title="isLiked ? '取消喜欢' : '喜欢'"
          @click="toggleLike"
        >
          <AppIcon :name="isLiked ? 'heart-filled' : 'heart'" :size="18" />
        </button>
      </template>
      <div v-else class="empty-left">
        <div class="mini-cover placeholder">
          <AppIcon name="disc" :size="22" />
        </div>
        <div class="track-meta">
          <div class="meta-title muted">未在播放</div>
          <div class="meta-owner">选一首开始吧</div>
        </div>
      </div>
    </div>

    <!-- 中间 40%：核心控制 -->
    <div class="player-center">
      <div class="control-row">
        <button
          class="icon-btn mode-btn"
          :title="modeLabel"
          @click="player.cyclePlayMode()"
        >
          <AppIcon :name="modeIcon" :size="18" />
        </button>
        <button class="icon-btn" title="上一首" :disabled="!hasQueue" @click="player.prev()">
          <AppIcon name="skip-back" :size="20" />
        </button>
        <button
          class="play-btn"
          :disabled="!canPlay"
          :title="isPlaying ? '暂停' : '播放'"
          @click="player.togglePlayPause()"
        >
          <LoadingDots v-if="isLoading" light />
          <AppIcon v-else :name="isPlaying ? 'pause' : 'play'" :size="22" />
        </button>
        <button class="icon-btn" title="下一首" :disabled="!hasQueue" @click="player.next()">
          <AppIcon name="skip-forward" :size="20" />
        </button>
        <button
          class="icon-btn queue-btn"
          title="播放队列"
          :class="{ active: ui.queueOpen }"
          @click="ui.toggleQueue()"
        >
          <AppIcon name="queue" :size="18" />
          <span v-if="hasQueue" class="queue-count">{{ player.queue.length }}</span>
        </button>
      </div>

      <div class="progress-row">
        <span class="time">{{ player.formattedCurrentTime }}</span>
        <ProgressBar />
        <span class="time">{{ player.formattedDuration }}</span>
      </div>
    </div>

    <!-- 右侧 30%：辅助操作 -->
    <div class="player-right">
      <VolumeControl />
      <button
        class="icon-btn"
        :class="{ active: ui.lyricsOverlayEnabled }"
        :title="ui.lyricsOverlayEnabled ? '关闭悬浮字幕' : '打开悬浮字幕'"
        :disabled="!isDesktop"
        @click="ui.toggleLyricsOverlay()"
      >
        <AppIcon name="subtitle" :size="18" />
      </button>
      <div v-if="isDesktop && ui.lyricsOverlayEnabled" class="lyrics-colors" aria-label="悬浮字幕颜色">
        <button
          v-for="color in ui.lyricsOverlayColors"
          :key="color"
          class="lyrics-color"
          :class="{ selected: color === ui.lyricsOverlayColor }"
          :style="{ backgroundColor: color }"
          :title="`字幕颜色 ${color}`"
          @click="ui.setLyricsOverlayColor(color)"
        />
      </div>
      <button class="icon-btn" title="画中画（暂未接入）" disabled>
        <AppIcon name="pip" :size="18" />
      </button>
      <button
        class="icon-btn"
        :title="isDownloading ? '下载中…' : '下载当前音频'"
        :disabled="!track || isDownloading"
        @click="player.downloadCurrent()"
      >
        <AppIcon name="download" :size="18" :class="{ 'spin-slow': isDownloading }" />
      </button>
      <button class="icon-btn" title="打开播放详情" :disabled="!track" @click="ui.openNowPlaying()">
        <AppIcon name="fullscreen" :size="18" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { usePlayerStore } from '@/stores/playerStore'
import { useLibraryStore } from '@/stores/libraryStore'
import { useUiStore } from '@/stores/uiStore'
import { mediaUrl } from '@/api/client'
import type { PlayMode, Track } from '@/types'
import AppIcon from '@/components/base/AppIcon.vue'
import LoadingDots from '@/components/base/LoadingDots.vue'
import ProgressBar from '@/components/ProgressBar.vue'
import VolumeControl from '@/components/VolumeControl.vue'

const player = usePlayerStore()
const library = useLibraryStore()
const ui = useUiStore()

const { currentTrack, videoInfo, isPlaying, isLoading, isDownloading } = storeToRefs(player)

// 当前展示的曲目：优先队列曲目，否则回退到裸 videoInfo（直接输入播放的场景）
const track = computed<Track | null>(() => {
  if (currentTrack.value) return currentTrack.value
  if (videoInfo.value) {
    return {
      trackId: videoInfo.value.trackId,
      bvid: videoInfo.value.bvid,
      cid: videoInfo.value.cid,
      title: videoInfo.value.title,
      owner: videoInfo.value.owner,
      cover: videoInfo.value.cover,
      duration: videoInfo.value.duration,
      playCount: videoInfo.value.playCount,
      publishedAt: videoInfo.value.publishedAt,
    }
  }
  return null
})

const hasQueue = computed(() => player.queue.length > 0)
const canPlay = computed(() => track.value !== null && !isLoading.value)
const isLiked = computed(() => (track.value ? library.isLiked(track.value.bvid) : false))
const isDesktop = computed(() => window.location.protocol === 'tauri:' || window.location.hostname === 'tauri.localhost')

const MODE_META: Record<PlayMode, { icon: string; label: string }> = {
  order: { icon: 'repeat', label: '顺序播放' },
  loop: { icon: 'repeat', label: '列表循环' },
  single: { icon: 'repeat-one', label: '单曲循环' },
  shuffle: { icon: 'shuffle', label: '随机播放' },
}
const modeIcon = computed(() => MODE_META[player.playMode].icon)
const modeLabel = computed(() => MODE_META[player.playMode].label)

function toggleLike() {
  if (track.value) library.toggleLike(track.value)
}
</script>

<style scoped>
.player-bar {
  height: var(--player-height);
  background: var(--color-bg-content);
  border-top: 1px solid var(--color-border);
  display: grid;
  grid-template-columns: 30% 40% 30%;
  align-items: center;
  padding: 0 20px;
  gap: 16px;
}

/* 左侧 */
.player-left,
.empty-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.mini-cover {
  position: relative;
  width: 48px;
  height: 48px;
  border-radius: var(--radius-small);
  overflow: hidden;
  flex-shrink: 0;
  cursor: pointer;
  background: var(--color-bg-hover);
}

.mini-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-fallback,
.mini-cover.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: var(--color-text-tertiary);
}

.mini-cover.placeholder {
  cursor: default;
}

.cover-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  color: #fff;
  opacity: 0;
  transition: opacity 160ms ease;
}

.mini-cover:hover .cover-mask {
  opacity: 1;
}

.expand-icon {
  transform: rotate(180deg);
}

.track-meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.meta-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.meta-title.muted {
  color: var(--color-text-secondary);
  font-weight: 400;
}

.meta-owner {
  font-size: 12px;
  color: var(--color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 中间 */
.player-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.control-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.play-btn {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: none;
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 160ms ease, transform 120ms ease;
  box-shadow: 0 2px 8px rgba(251, 114, 153, 0.35);
}

.play-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.play-btn:active:not(:disabled) {
  transform: scale(0.94);
}

.play-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.progress-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  max-width: 520px;
}

.time {
  font-size: 11px;
  color: var(--color-text-tertiary);
  font-variant-numeric: tabular-nums;
  min-width: 38px;
  text-align: center;
}

/* 右侧 */
.player-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
}

/* 通用图标按钮 */
.icon-btn {
  position: relative;
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  border-radius: 50%;
  cursor: pointer;
  transition: background 160ms ease, color 160ms ease;
}

.icon-btn:hover:not(:disabled) {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.icon-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.icon-btn.active,
.mode-btn.active {
  color: var(--color-primary);
}

.like-btn.liked {
  color: var(--color-primary);
}

.queue-btn.active {
  color: var(--color-primary);
}

.lyrics-colors {
  height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 0 7px;
  border-radius: 999px;
  background: var(--color-bg-hover);
}

.lyrics-color {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.52);
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.14);
}

.lyrics-color.selected {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(251, 114, 153, 0.24);
}

.queue-count {
  position: absolute;
  top: 0;
  right: 0;
  min-width: 15px;
  height: 15px;
  padding: 0 3px;
  border-radius: 8px;
  background: var(--color-primary);
  color: #fff;
  font-size: 10px;
  line-height: 15px;
  text-align: center;
}

.spin-slow {
  animation: spin-slow 1.2s linear infinite;
}

@keyframes spin-slow {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .spin-slow { animation: none; }
}

@media (max-width: 720px) {
  .player-bar {
    grid-template-columns: minmax(0, 1fr);
    padding: 0 10px;
    gap: 0;
  }

  .player-left,
  .player-right {
    display: none;
  }

  .player-center {
    min-width: 0;
  }

  .control-row {
    gap: 10px;
  }

  .progress-row {
    max-width: 390px;
  }
}
</style>
