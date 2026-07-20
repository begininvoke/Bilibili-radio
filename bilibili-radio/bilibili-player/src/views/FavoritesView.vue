<template>
  <div class="page favorites">
    <!-- 收藏夹列表：封面卡片 -->
    <template v-if="!activeFolder">
      <header class="fav-header">
        <h1>B站收藏夹</h1>
        <span class="mock-tag">示例数据</span>
      </header>
      <div class="folder-grid">
        <div
          v-for="f in favoriteFolders"
          :key="f.id"
          class="folder-card"
          @click="openFolder(f.id)"
        >
          <div class="folder-cover">
            <img :src="f.cover" :alt="f.title" loading="lazy" />
            <span class="folder-count">{{ f.count }}</span>
          </div>
          <div class="folder-title">{{ f.title }}</div>
        </div>
      </div>
    </template>

    <!-- 收藏夹内容：紧凑行列表 -->
    <template v-else>
      <header class="detail-header">
        <button class="back-btn" @click="closeFolder">
          <AppIcon name="chevron" :size="18" class="back-icon" />
          <span>全部收藏夹</span>
        </button>
      </header>
      <div class="detail-top">
        <img class="detail-cover" :src="activeFolder.cover" :alt="activeFolder.title" />
        <div class="detail-info">
          <span class="detail-kind">收藏夹</span>
          <h1 class="detail-title">{{ activeFolder.title }}</h1>
          <p class="detail-meta">{{ activeFolder.count }} 个内容</p>
          <div class="detail-actions">
            <button class="primary-btn" @click="playAll">
              <AppIcon name="play" :size="16" />
              <span>播放全部</span>
            </button>
            <button class="ghost-btn" @click="importAsPlaylist">
              <AppIcon name="import" :size="16" />
              <span>导入为本地歌单</span>
            </button>
          </div>
        </div>
      </div>
      <div class="result-list">
        <TrackRow
          v-for="(t, i) in activeFolder.tracks"
          :key="t.bvid"
          :track="t"
          :index="i"
          :is-current="isCurrent(t.bvid)"
          :is-playing="isPlaying && isCurrent(t.bvid)"
          :is-liked="library.isLiked(t.bvid)"
          @play="player.playList(activeFolder.tracks, i)"
          @like="library.toggleLike(t)"
          @enqueue="player.enqueue(t)"
        />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { usePlayerStore } from '@/stores/playerStore'
import { useLibraryStore } from '@/stores/libraryStore'
import { favoriteFolders, getFavFolder } from '@/mock/data'
import AppIcon from '@/components/base/AppIcon.vue'
import TrackRow from '@/components/TrackRow.vue'

const route = useRoute()
const router = useRouter()
const player = usePlayerStore()
const library = useLibraryStore()
const { currentTrack, isPlaying } = storeToRefs(player)

const activeFolder = computed(() => {
  const id = route.query.folder as string | undefined
  return id ? getFavFolder(id) : undefined
})

function openFolder(id: string) {
  router.push({ path: '/favorites', query: { folder: id } })
}

function closeFolder() {
  router.push({ path: '/favorites' })
}

function isCurrent(bvid: string): boolean {
  return currentTrack.value?.bvid === bvid
}

function playAll() {
  if (activeFolder.value) player.playList(activeFolder.value.tracks, 0)
}

function importAsPlaylist() {
  if (!activeFolder.value) return
  library.createPlaylist(activeFolder.value.title, activeFolder.value.tracks)
  window.alert(`已导入为本地歌单：${activeFolder.value.title}`)
}
</script>

<style scoped>
.page {
  padding: 24px 32px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.fav-header,
.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.fav-header h1 {
  font-size: 26px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.mock-tag {
  font-size: 11px;
  color: var(--color-text-tertiary);
  padding: 2px 8px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
}

.folder-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 20px;
}

.folder-card {
  cursor: pointer;
}

.folder-cover {
  position: relative;
  aspect-ratio: 16 / 10;
  border-radius: var(--radius-medium);
  overflow: hidden;
  background: var(--color-bg-hover);
}

.folder-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 300ms ease;
}

.folder-card:hover .folder-cover img {
  transform: scale(1.04);
}

.folder-count {
  position: absolute;
  right: 8px;
  top: 8px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 11px;
}

.folder-title {
  margin-top: 10px;
  font-size: 14px;
  color: var(--color-text-primary);
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 14px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: var(--radius-small);
  transition: background 160ms ease, color 160ms ease;
}

.back-btn:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.back-icon {
  transform: rotate(90deg);
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
  object-fit: cover;
  box-shadow: var(--shadow-popup);
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
  transition: background 160ms ease, border-color 160ms ease;
}

.primary-btn {
  border: none;
  background: var(--color-primary);
  color: #fff;
}

.primary-btn:hover {
  background: var(--color-primary-hover);
}

.ghost-btn {
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text-primary);
}

.ghost-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.result-list {
  display: flex;
  flex-direction: column;
}
</style>
