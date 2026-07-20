<template>
  <div class="now-playing">
    <!-- 品牌氛围背景：模糊封面单独分层，绝不给容器加 filter -->
    <div class="ambient" :class="{ still: reducedMotion || !isPlaying }">
      <div
        v-for="n in 3"
        :key="n"
        class="ambient-layer"
        :class="`layer-${n}`"
        :style="coverStyle"
      />
    </div>
    <div class="ambient-mask" />

    <!-- 顶部栏 -->
    <header class="np-header">
      <button class="np-icon-btn" title="收起" @click="ui.closeNowPlaying()">
        <AppIcon name="chevron-down" :size="22" />
      </button>
      <span class="np-brand">正在播放</span>
      <div class="np-spacer" />
    </header>

    <div class="np-body">
      <!-- 左侧：黑胶 + 唱针 -->
      <div class="disc-side">
        <div class="tonearm" :class="{ playing: isPlaying }">
          <svg viewBox="0 0 60 120" fill="none" aria-hidden="true">
            <circle cx="12" cy="12" r="8" fill="#3a3a3f" />
            <circle cx="12" cy="12" r="3" fill="#5a5a60" />
            <rect x="9" y="12" width="6" height="70" rx="3" fill="#48484e" transform="rotate(-18 12 12)" />
            <rect x="30" y="72" width="14" height="20" rx="3" fill="#3a3a3f" transform="rotate(-18 12 12)" />
          </svg>
        </div>

        <div class="vinyl" :class="{ spinning: isPlaying, paused: !isPlaying }">
          <div class="vinyl-disc">
            <div class="vinyl-grooves" />
            <div class="vinyl-label">
              <img v-if="track?.cover" :src="mediaUrl(track.cover)" :alt="track?.title" />
              <div v-else class="label-fallback">
                <AppIcon name="disc" :size="40" />
              </div>
            </div>
            <div class="vinyl-hole" />
          </div>
        </div>
      </div>

      <!-- 右侧：信息区 -->
      <div class="info-side">
        <div class="track-head">
          <h1 class="np-title" :title="track?.title">{{ track?.title || '未在播放' }}</h1>
          <p class="np-owner">{{ ownerLine }}</p>
          <p class="np-stats">{{ statsLine }}</p>
          <div class="detail-actions">
            <button class="detail-btn" :disabled="!track" title="加入播放队列" @click="enqueueCurrent">
              <AppIcon name="plus" :size="16" />
              <span>加入队列</span>
            </button>
            <button class="detail-btn" :disabled="!track" title="添加到歌单" @click="playlistMenuOpen = !playlistMenuOpen">
              <AppIcon name="list" :size="16" />
              <span>添加到歌单</span>
            </button>
            <button
              class="detail-btn"
              :title="isDownloading ? '下载中…' : '下载当前音频'"
              :disabled="!track || isDownloading"
              @click="player.downloadCurrent()"
            >
              <AppIcon name="download" :size="16" :class="{ 'spin-slow': isDownloading }" />
              <span>{{ isDownloading ? '下载中' : '下载' }}</span>
            </button>
          </div>
          <div v-if="playlistMenuOpen" class="playlist-menu">
            <button
              v-for="playlist in library.playlists"
              :key="playlist.id"
              class="playlist-option"
              :disabled="!track || library.hasPlaylistTrack(playlist.id, track)"
              @click="addCurrentToPlaylist(playlist.id)"
            >
              <AppIcon name="list" :size="14" />
              <span>{{ playlist.name }}</span>
              <small v-if="track && library.hasPlaylistTrack(playlist.id, track)">已存在</small>
            </button>
            <p v-if="library.playlists.length === 0" class="playlist-empty">先在侧边栏新建歌单</p>
          </div>
        </div>

        <div class="info-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="tab-btn"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>

        <div class="info-panel">
          <template v-if="activeTab === 'intro'">
            <p class="panel-text muted">简介接口正在开发中。</p>
          </template>
          <template v-else-if="activeTab === 'subtitle'">
            <p class="panel-text muted">字幕接口正在开发中。</p>
          </template>
          <template v-else-if="activeTab === 'chapters'">
            <p class="panel-text muted">章节接口正在开发中。</p>
          </template>
          <template v-else>
            <p class="panel-text muted">评论区接口正在开发中。</p>
          </template>
        </div>
      </div>
    </div>

    <!-- 底部进度 + 控制 -->
    <footer class="np-footer">
      <div class="np-progress">
        <span class="np-time">{{ player.formattedCurrentTime }}</span>
        <ProgressBar />
        <span class="np-time">{{ player.formattedDuration }}</span>
      </div>
      <div class="np-controls">
        <button class="np-ctrl" :title="modeLabel" @click="player.cyclePlayMode()">
          <AppIcon :name="modeIcon" :size="20" />
        </button>
        <button class="np-ctrl" title="上一首" :disabled="!hasQueue" @click="player.prev()">
          <AppIcon name="skip-back" :size="24" />
        </button>
        <button class="np-play" :disabled="!track" @click="player.togglePlayPause()">
          <AppIcon :name="isPlaying ? 'pause' : 'play'" :size="26" />
        </button>
        <button class="np-ctrl" title="下一首" :disabled="!hasQueue" @click="player.next()">
          <AppIcon name="skip-forward" :size="24" />
        </button>
        <button
          class="np-ctrl"
          :class="{ liked: isLiked }"
          :title="isLiked ? '取消喜欢' : '喜欢'"
          @click="toggleLike"
        >
          <AppIcon :name="isLiked ? 'heart-filled' : 'heart'" :size="20" />
        </button>
        <button
          class="np-ctrl"
          :title="isDownloading ? '下载中…' : '下载当前音频'"
          :disabled="!track || isDownloading"
          @click="player.downloadCurrent()"
        >
          <AppIcon name="download" :size="20" :class="{ 'spin-slow': isDownloading }" />
        </button>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { usePlayerStore } from '@/stores/playerStore'
import { useLibraryStore } from '@/stores/libraryStore'
import { useUiStore } from '@/stores/uiStore'
import { mediaUrl } from '@/api/client'
import type { PlayMode, Track } from '@/types'
import AppIcon from '@/components/base/AppIcon.vue'
import ProgressBar from '@/components/ProgressBar.vue'

const player = usePlayerStore()
const library = useLibraryStore()
const ui = useUiStore()

const { currentTrack, videoInfo, isPlaying, isDownloading } = storeToRefs(player)
const reducedMotion = computed(() => ui.reducedMotion)

const track = computed<Track | null>(() => {
  if (currentTrack.value) return currentTrack.value
  if (videoInfo.value) {
    return {
      bvid: videoInfo.value.bvid,
      title: videoInfo.value.title,
      owner: videoInfo.value.owner,
      cover: videoInfo.value.cover,
      duration: videoInfo.value.duration,
    }
  }
  return null
})

const coverStyle = computed(() => ({
  backgroundImage: track.value?.cover ? `url("${mediaUrl(track.value.cover).replace(/"/g, '%22')}")` : 'none',
}))

const hasQueue = computed(() => player.queue.length > 0)
const isLiked = computed(() => (track.value ? library.isLiked(track.value.bvid) : false))
const ownerLine = computed(() => (track.value ? `${track.value.owner} · B站` : ''))
const statsLine = computed(() => (track.value ? track.value.bvid : ''))

const MODE_META: Record<PlayMode, { icon: string; label: string }> = {
  order: { icon: 'repeat', label: '顺序播放' },
  loop: { icon: 'repeat', label: '列表循环' },
  single: { icon: 'repeat-one', label: '单曲循环' },
  shuffle: { icon: 'shuffle', label: '随机播放' },
}
const modeIcon = computed(() => MODE_META[player.playMode].icon)
const modeLabel = computed(() => MODE_META[player.playMode].label)

type TabKey = 'subtitle' | 'intro' | 'chapters' | 'comments'
const activeTab = ref<TabKey>('intro')
const tabs: { key: TabKey; label: string }[] = [
  { key: 'subtitle', label: '字幕' },
  { key: 'intro', label: '简介' },
  { key: 'chapters', label: '章节' },
  { key: 'comments', label: '评论区' },
]
const playlistMenuOpen = ref(false)

function toggleLike() {
  if (track.value) library.toggleLike(track.value)
}

function enqueueCurrent() {
  if (track.value) player.enqueue(track.value)
}

function addCurrentToPlaylist(playlistId: string) {
  if (!track.value) return
  library.addToPlaylist(playlistId, track.value)
  playlistMenuOpen.value = false
}
</script>

<style scoped>
.now-playing {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #0e0e12;
  color: #fff;
}

/* ===== 品牌氛围背景（低频缓动模糊封面）===== */
.ambient {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.ambient-layer {
  position: absolute;
  inset: -80px;
  background-position: center;
  background-size: cover;
  filter: blur(60px);
  transform: scale(1.15);
  will-change: transform;
}

.layer-1 {
  opacity: 0.9;
  animation: drift1 40s ease-in-out infinite;
}
.layer-2 {
  opacity: 0.5;
  mix-blend-mode: screen;
  animation: drift2 55s ease-in-out infinite;
}
.layer-3 {
  opacity: 0.35;
  mix-blend-mode: overlay;
  animation: drift3 70s ease-in-out infinite;
}

/* 动画非常慢、幅度很小，符合方案 0.08~0.15 的缓动基调 */
@keyframes drift1 {
  0%, 100% { transform: scale(1.15) translate(0, 0); }
  50% { transform: scale(1.2) translate(2%, -1.5%); }
}
@keyframes drift2 {
  0%, 100% { transform: scale(1.18) translate(0, 0) rotate(0deg); }
  50% { transform: scale(1.22) translate(-2%, 1.5%) rotate(1.5deg); }
}
@keyframes drift3 {
  0%, 100% { transform: scale(1.2) translate(0, 0); }
  50% { transform: scale(1.15) translate(1.5%, 2%); }
}

/* 降级：低性能 / reduced-motion / 暂停时静止为纯模糊封面 */
.ambient.still .ambient-layer {
  animation: none;
}

.ambient-mask {
  position: absolute;
  inset: 0;
  z-index: 1;
  background: linear-gradient(rgba(10, 10, 14, 0.55), rgba(10, 10, 14, 0.72));
}

/* ===== 顶栏 ===== */
.np-header {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  height: 56px;
  padding: 0 20px;
}

.np-icon-btn {
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  border-radius: 50%;
  cursor: pointer;
  transition: background 160ms ease;
}
.np-icon-btn:hover {
  background: rgba(255, 255, 255, 0.16);
}

.np-brand {
  flex: 1;
  text-align: center;
  font-size: 14px;
  letter-spacing: 1px;
  color: rgba(255, 255, 255, 0.8);
}
.np-spacer {
  width: 38px;
}

/* ===== 主体 ===== */
.np-body {
  position: relative;
  z-index: 2;
  flex: 1;
  display: flex;
  align-items: center;
  gap: 64px;
  padding: 0 8%;
  min-height: 0;
}

/* 黑胶 */
.disc-side {
  position: relative;
  flex-shrink: 0;
  width: 380px;
  height: 380px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.vinyl {
  width: 340px;
  height: 340px;
}

.vinyl-disc {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: radial-gradient(circle at center, #2a2a2f 0%, #141417 60%, #0c0c0f 100%);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
}

.vinyl.spinning {
  animation: spin 18s linear infinite;
}
.vinyl.paused {
  animation: spin 18s linear infinite;
  animation-play-state: paused;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.vinyl-grooves {
  position: absolute;
  inset: 20px;
  border-radius: 50%;
  background: repeating-radial-gradient(
    circle at center,
    rgba(255, 255, 255, 0.03) 0px,
    rgba(255, 255, 255, 0.03) 1px,
    transparent 2px,
    transparent 5px
  );
}

.vinyl-label {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 44%;
  height: 44%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  overflow: hidden;
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.06);
}

.vinyl-label img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.label-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #26262b;
  color: rgba(255, 255, 255, 0.5);
}

.vinyl-hole {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 12px;
  height: 12px;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background: #0e0e12;
  box-shadow: inset 0 0 3px rgba(255, 255, 255, 0.3);
}

/* 唱针 */
.tonearm {
  position: absolute;
  top: -10px;
  right: 40px;
  z-index: 3;
  width: 60px;
  height: 120px;
  transform-origin: 12px 12px;
  transform: rotate(-22deg);
  transition: transform 500ms ease;
}
.tonearm.playing {
  transform: rotate(0deg);
}

/* 信息区 */
.info-side {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 560px;
}

.np-title {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.np-owner {
  margin-top: 10px;
  font-size: 15px;
  color: rgba(255, 255, 255, 0.75);
}

.np-stats {
  margin-top: 6px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  font-variant-numeric: tabular-nums;
}

.detail-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
  flex-wrap: wrap;
}

.detail-btn {
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 12px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: var(--radius-small);
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.86);
  font-size: 13px;
  cursor: pointer;
  transition: background 160ms ease, border-color 160ms ease, color 160ms ease;
}

.detail-btn:hover:not(:disabled) {
  background: rgba(251, 114, 153, 0.18);
  border-color: rgba(251, 114, 153, 0.42);
  color: #fff;
}

.detail-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.playlist-menu {
  margin-top: 10px;
  width: min(360px, 100%);
  display: grid;
  gap: 6px;
  padding: 8px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: var(--radius-medium);
  background: rgba(12, 12, 16, 0.6);
}

.playlist-option {
  min-width: 0;
  height: 32px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 9px;
  border: none;
  border-radius: var(--radius-small);
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.86);
  cursor: pointer;
  transition: background 160ms ease, color 160ms ease;
}

.playlist-option:hover:not(:disabled) {
  background: rgba(251, 114, 153, 0.2);
  color: #fff;
}

.playlist-option:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.playlist-option span {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  text-align: left;
}

.playlist-option small,
.playlist-empty {
  flex-shrink: 0;
  color: rgba(255, 255, 255, 0.46);
  font-size: 12px;
}

.playlist-empty {
  padding: 4px 2px;
}

.info-tabs {
  display: flex;
  gap: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  padding-bottom: 4px;
}

.tab-btn {
  padding: 6px 14px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
  cursor: pointer;
  border-radius: var(--radius-small);
  transition: color 160ms ease, background 160ms ease;
}
.tab-btn:hover {
  color: #fff;
}
.tab-btn.active {
  color: var(--color-primary);
}

.info-panel {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.panel-text {
  font-size: 14px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.82);
}
.panel-text.muted {
  color: rgba(255, 255, 255, 0.5);
}

/* ===== 底部 ===== */
.np-footer {
  position: relative;
  z-index: 2;
  padding: 20px 8% 32px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.np-progress {
  display: flex;
  align-items: center;
  gap: 12px;
}

.np-time {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  font-variant-numeric: tabular-nums;
  min-width: 42px;
  text-align: center;
}

.np-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
}

.np-ctrl {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.85);
  border-radius: 50%;
  cursor: pointer;
  transition: background 160ms ease, color 160ms ease;
}
.np-ctrl:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}
.np-ctrl:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.np-ctrl.liked {
  color: var(--color-primary);
}

.np-play {
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: var(--color-primary);
  color: #fff;
  border-radius: 50%;
  cursor: pointer;
  transition: background 160ms ease, transform 120ms ease;
  box-shadow: 0 4px 16px rgba(251, 114, 153, 0.5);
}
.np-play:hover:not(:disabled) {
  background: var(--color-primary-hover);
}
.np-play:active:not(:disabled) {
  transform: scale(0.94);
}
.np-play:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 响应式：窄屏堆叠 */
@media (max-width: 900px) {
  .np-body {
    flex-direction: column;
    justify-content: center;
    gap: 32px;
    padding: 0 24px;
    overflow-y: auto;
  }
  .disc-side {
    width: 260px;
    height: 260px;
  }
  .vinyl {
    width: 240px;
    height: 240px;
  }
}

.np-ctrl .spin-slow {
  animation: spin 1.2s linear infinite;
}

@media (prefers-reduced-motion: reduce) {
  .vinyl.spinning { animation: none; }
  .ambient-layer { animation: none !important; }
  .tonearm { transition: none; }
  .np-ctrl .spin-slow { animation: none; }
}
</style>
