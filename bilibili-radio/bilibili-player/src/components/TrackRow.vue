<template>
  <div
    class="track-row-wrap"
    @mouseenter="handleMouseEnter"
    @mouseleave="handleMouseLeave"
  >
    <div
      class="track-row"
      :class="{ active: isCurrent }"
      @dblclick="handlePrimaryPlay"
    >
      <div class="col-index">
        <PlayingBars v-if="isCurrent && isPlaying" />
        <span v-else class="index-num">{{ index + 1 }}</span>
        <button class="row-play" title="播放" @click.stop="handlePrimaryPlay">
          <AppIcon name="play" :size="16" />
        </button>
      </div>

      <img class="col-cover" :src="mediaUrl(track.cover)" :alt="track.title" loading="lazy" />

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
        <button class="action-btn" title="添加到队列" @click.stop="handleEnqueue">
          <AppIcon name="plus" :size="16" />
        </button>
      </div>
    </div>

    <div
      v-if="showPartsPanel"
      class="parts-popover"
      @click.stop
    >
      <div class="parts-head">
        <div>
          <div class="parts-title">分 P 列表</div>
          <div class="parts-sub">{{ parts.length || 0 }} 个内容</div>
        </div>
        <select
          v-if="library.playlists.length"
          v-model="selectedPlaylistId"
          class="playlist-select"
          title="选择要加入的歌单"
        >
          <option value="">选择歌单</option>
          <option v-for="playlist in library.playlists" :key="playlist.id" :value="playlist.id">
            {{ playlist.name }}
          </option>
        </select>
        <span v-else class="playlist-empty">先创建歌单</span>
      </div>

      <div v-if="partsLoading" class="parts-state">正在读取分 P</div>
      <div v-else-if="partsError" class="parts-state error">{{ partsError }}</div>
      <div v-else class="parts-list">
        <div v-for="part in parts" :key="part.trackId ?? `${part.bvid}:${part.cid}`" class="part-row">
          <img class="part-cover" :src="mediaUrl(part.cover)" :alt="partDisplayTitle(part)" loading="lazy" />
          <div class="part-main">
            <div class="part-title" :title="part.title">
              <span class="part-index">P{{ part.page ?? '?' }}</span>
              <span>{{ partDisplayTitle(part) }}</span>
            </div>
            <div class="part-meta">
              <span>{{ formatDuration(part.duration) }}</span>
              <span v-if="part.owner">{{ part.owner }}</span>
            </div>
          </div>
          <div class="part-actions">
            <button class="part-btn primary" title="播放此 P" @click="playPart(part)">
              <AppIcon name="play" :size="14" />
            </button>
            <button class="part-btn" title="加入队列" @click="enqueuePart(part)">
              <AppIcon name="plus" :size="14" />
            </button>
            <button
              class="part-btn"
              :class="{ liked: library.isTrackLiked(part) }"
              :title="library.isTrackLiked(part) ? '取消收藏此 P' : '收藏此 P'"
              @click="toggleLikePart(part)"
            >
              <AppIcon :name="library.isTrackLiked(part) ? 'heart-filled' : 'heart'" :size="14" />
            </button>
            <button
              class="part-btn"
              :disabled="!activePlaylistId || isInActivePlaylist(part)"
              :title="playlistButtonTitle(part)"
              @click="addPartToPlaylist(part)"
            >
              <AppIcon name="list" :size="14" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Track } from '@/types'
import { getTrackDetail, mediaUrl } from '@/api/client'
import { useLibraryStore } from '@/stores/libraryStore'
import { usePlayerStore } from '@/stores/playerStore'
import { formatDuration } from '@/utils/format'
import AppIcon from '@/components/base/AppIcon.vue'
import PlayingBars from '@/components/base/PlayingBars.vue'

const props = defineProps<{
  track: Track
  index: number
  isCurrent?: boolean
  isPlaying?: boolean
  isLiked?: boolean
}>()

const emit = defineEmits<{
  play: []
  like: []
  enqueue: []
}>()

const player = usePlayerStore()
const library = useLibraryStore()

const parts = ref<Track[]>([])
const partsOpen = ref(false)
const partsLoading = ref(false)
const partsLoaded = ref(false)
const partsError = ref<string | null>(null)
const loadedBvid = ref<string | null>(null)
const selectedPlaylistId = ref('')

let loadPromise: Promise<Track[]> | null = null

const isVideoLevelTrack = computed(() => props.track.cid == null)
const activePlaylistId = computed(() => {
  const selected = library.playlists.find((playlist) => playlist.id === selectedPlaylistId.value)
  return selected?.id ?? ''
})
const showPartsPanel = computed(() => {
  return isVideoLevelTrack.value && partsOpen.value && (partsLoading.value || !!partsError.value || parts.value.length > 1)
})

function resetPartsIfTrackChanged() {
  if (loadedBvid.value === props.track.bvid) return
  loadedBvid.value = props.track.bvid
  parts.value = []
  partsLoaded.value = false
  partsError.value = null
  loadPromise = null
}

async function ensureParts(): Promise<Track[]> {
  if (!isVideoLevelTrack.value) return []
  resetPartsIfTrackChanged()
  if (partsLoaded.value) return parts.value
  if (loadPromise) return loadPromise

  partsLoading.value = true
  partsError.value = null
  loadPromise = getTrackDetail(props.track.bvid)
    .then((detail) => {
      const detailParts = detail.pages.length ? detail.pages : [detail.track]
      parts.value = detailParts
        .filter((part) => part.cid != null)
        .map((part) => ({
          ...props.track,
          ...part,
          cover: part.cover || props.track.cover,
          owner: part.owner || props.track.owner,
          playCount: part.playCount ?? props.track.playCount,
          publishedAt: part.publishedAt ?? props.track.publishedAt,
          source: part.source ?? props.track.source,
        }))
      partsLoaded.value = true
      return parts.value
    })
    .catch((error) => {
      partsError.value = error instanceof Error ? error.message : '分 P 读取失败'
      return []
    })
    .finally(() => {
      partsLoading.value = false
      loadPromise = null
    })

  return loadPromise
}

function handleMouseEnter() {
  if (!isVideoLevelTrack.value) return
  ensureDefaultPlaylist()
  partsOpen.value = true
  void ensureParts()
}

function handleMouseLeave() {
  partsOpen.value = false
}

async function handlePrimaryPlay() {
  if (!isVideoLevelTrack.value) {
    emit('play')
    return
  }
  const pageTracks = await ensureParts()
  if (pageTracks.length > 1) {
    partsOpen.value = true
    return
  }
  if (pageTracks[0]) {
    player.playTrack(pageTracks[0])
    return
  }
  emit('play')
}

async function handleEnqueue() {
  if (!isVideoLevelTrack.value) {
    emit('enqueue')
    return
  }
  const pageTracks = await ensureParts()
  if (pageTracks.length > 1) {
    partsOpen.value = true
    return
  }
  if (pageTracks[0]) {
    player.enqueue(pageTracks[0])
    return
  }
  emit('enqueue')
}

function partDisplayTitle(part: Track): string {
  return part.pageTitle || part.title
}

function playPart(part: Track) {
  partsOpen.value = false
  player.playTrack(part)
}

function enqueuePart(part: Track) {
  player.enqueue(part)
}

function toggleLikePart(part: Track) {
  library.toggleLike(part)
}

function addPartToPlaylist(part: Track) {
  ensureDefaultPlaylist()
  const id = activePlaylistId.value
  if (!id) return
  library.addToPlaylist(id, part)
}

function ensureDefaultPlaylist() {
  if (!library.playlists.length) {
    selectedPlaylistId.value = ''
    return
  }
  if (!library.playlists.some((playlist) => playlist.id === selectedPlaylistId.value)) {
    selectedPlaylistId.value = library.playlists[0].id
  }
}

function isInActivePlaylist(part: Track): boolean {
  const id = activePlaylistId.value
  return !!id && library.hasPlaylistTrack(id, part)
}

function playlistButtonTitle(part: Track): string {
  if (!activePlaylistId.value) return '先创建歌单'
  return isInActivePlaylist(part) ? '已在歌单中' : '加入所选歌单'
}
</script>

<style scoped>
.track-row-wrap {
  position: relative;
  min-width: 0;
}

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

.track-row .col-actions:has(.liked) {
  opacity: 1;
}

.parts-popover {
  position: absolute;
  top: 58px;
  left: 72px;
  z-index: 40;
  width: min(520px, calc(100vw - 340px));
  max-height: 300px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(251, 114, 153, 0.28);
  border-radius: var(--radius-medium);
  background: color-mix(in srgb, var(--color-bg-content) 96%, var(--color-primary) 4%);
  box-shadow: var(--shadow-popup);
}

.parts-head {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: space-between;
  padding: 12px;
  border-bottom: 1px solid var(--color-border);
}

.parts-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.parts-sub,
.playlist-empty {
  margin-top: 2px;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.playlist-select {
  max-width: 168px;
  height: 30px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-small);
  padding: 0 9px;
  background: var(--color-bg-app);
  color: var(--color-text-primary);
  font-size: 12px;
  outline: none;
}

.parts-state {
  min-height: 72px;
  display: grid;
  place-items: center;
  padding: 16px;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.parts-state.error {
  color: var(--color-primary);
}

.parts-list {
  overflow-y: auto;
  padding: 6px;
}

.part-row {
  display: grid;
  grid-template-columns: 44px 1fr auto;
  align-items: center;
  gap: 10px;
  min-height: 56px;
  padding: 6px;
  border-radius: var(--radius-small);
}

.part-row:hover {
  background: var(--color-bg-hover);
}

.part-cover {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-small);
  object-fit: cover;
  background: var(--color-bg-hover);
}

.part-main {
  min-width: 0;
}

.part-title {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-size: 13px;
  color: var(--color-text-primary);
}

.part-title span:last-child {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.part-index {
  flex-shrink: 0;
  color: var(--color-primary);
  font-weight: 700;
}

.part-meta {
  display: flex;
  gap: 8px;
  margin-top: 3px;
  font-size: 11px;
  color: var(--color-text-secondary);
}

.part-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.part-btn {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background 160ms ease, color 160ms ease;
}

.part-btn:hover:not(:disabled),
.part-btn.primary {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.part-btn.liked {
  color: var(--color-primary);
}

.part-btn:disabled {
  opacity: 0.38;
  cursor: not-allowed;
}

@media (max-width: 720px) {
  .parts-popover {
    left: 12px;
    width: calc(100vw - 64px);
  }

  .parts-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .playlist-select {
    width: 100%;
    max-width: none;
  }
}
</style>
