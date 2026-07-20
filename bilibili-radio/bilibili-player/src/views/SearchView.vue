<template>
  <div class="page search">
    <header class="search-head">
      <h1>搜索</h1>
      <p class="hint">搜索 B站视频并直接加入播放队列；BV 号或视频链接仍可直接播放。</p>

      <form class="search-box" @submit.prevent="handleSearch">
        <AppIcon name="search" :size="18" class="search-icon" />
        <input
          v-model="input"
          type="text"
          placeholder="搜索关键词、BV 号或 bilibili.com 视频链接"
          autocomplete="off"
        />
        <button class="search-btn" type="submit" :disabled="!input.trim() || searchLoading">
          <LoadingDots v-if="searchLoading" light />
          <span v-else>搜索</span>
        </button>
        <button
          v-if="canDirectPlay"
          class="play-btn"
          type="button"
          :disabled="isLoading"
          @click="handlePlay"
        >
          <AppIcon name="play" :size="14" />
          <span>播放</span>
        </button>
      </form>

      <p v-if="searchError" class="error">{{ searchError }}</p>
      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
    </header>

    <section v-if="track" class="section">
      <SectionHeader title="正在播放" />
      <div class="result-list">
        <TrackRow
          :track="track"
          :index="0"
          :is-current="true"
          :is-playing="isPlaying"
          :is-liked="library.isLiked(track.bvid)"
          @play="player.playTrack(track)"
          @like="library.toggleLike(track)"
          @enqueue="player.enqueue(track)"
        />
      </div>
    </section>

    <section class="section">
      <SectionHeader
        :title="searchedKeyword ? `搜索结果：${searchedKeyword}` : '搜索结果'"
        :count="results.length"
      />

      <div v-if="searchLoading" class="loading-state">
        <LoadingDots />
        <span>正在搜索</span>
      </div>

      <div v-else-if="searchedKeyword && results.length === 0" class="empty-state">
        没有找到相关内容
      </div>

      <div v-else class="result-list">
        <TrackRow
          v-for="(t, i) in results"
          :key="t.trackId ?? `${t.bvid}:${t.cid ?? i}`"
          :track="t"
          :index="i"
          :is-current="isCurrent(t)"
          :is-playing="isPlaying && isCurrent(t)"
          :is-liked="library.isLiked(t.bvid)"
          @play="player.playTrack(t)"
          @like="library.toggleLike(t)"
          @enqueue="player.enqueue(t)"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { ApiError, searchTracks } from '@/api/client'
import { usePlayerStore } from '@/stores/playerStore'
import { useLibraryStore } from '@/stores/libraryStore'
import type { Track } from '@/types'
import AppIcon from '@/components/base/AppIcon.vue'
import LoadingDots from '@/components/base/LoadingDots.vue'
import TrackRow from '@/components/TrackRow.vue'
import SectionHeader from '@/components/base/SectionHeader.vue'

const route = useRoute()
const player = usePlayerStore()
const library = useLibraryStore()
const { currentTrack, videoInfo, isPlaying, isLoading, errorMessage } = storeToRefs(player)

const input = ref('')
const results = ref<Track[]>([])
const searchedKeyword = ref('')
const searchLoading = ref(false)
const searchError = ref<string | null>(null)

const pageSize = 20
let searchSeq = 0

watch(
  () => route.query.q,
  (q) => {
    if (typeof q === 'string' && q.trim()) {
      input.value = q
      void handleSearch()
    }
  },
  { immediate: true }
)

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

const canDirectPlay = computed(() => looksLikeBiliInput(input.value.trim()))

function isCurrent(candidate: Track): boolean {
  const current = track.value
  if (!current) return false
  if (current.trackId && candidate.trackId) return current.trackId === candidate.trackId
  return current.bvid === candidate.bvid && (candidate.cid == null || current.cid == null || current.cid === candidate.cid)
}

async function handleSearch() {
  const keyword = input.value.trim()
  if (!keyword) return

  const seq = ++searchSeq
  searchLoading.value = true
  searchError.value = null

  try {
    const data = await searchTracks(keyword, 1, pageSize)
    if (seq !== searchSeq) return
    results.value = data.tracks
    searchedKeyword.value = keyword
  } catch (error) {
    if (seq !== searchSeq) return
    results.value = []
    searchedKeyword.value = keyword
    searchError.value = error instanceof ApiError ? error.message : '搜索失败'
  } finally {
    if (seq === searchSeq) {
      searchLoading.value = false
    }
  }
}

function handlePlay() {
  const value = input.value.trim()
  if (value) {
    player.playInput(value)
  }
}

function looksLikeBiliInput(value: string): boolean {
  return /^(BV|bv)[0-9A-Za-z]{10}$/.test(value) || /bilibili\.com\/video\/(BV|bv)[0-9A-Za-z]{10}/.test(value)
}
</script>

<style scoped>
.page {
  padding: 24px 32px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.search-head h1 {
  font-size: 26px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.hint {
  margin-top: 6px;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.search-box {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 760px;
  min-height: 44px;
  padding: 6px 6px 6px 14px;
  background: var(--color-bg-app);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-medium);
  transition: border-color 160ms ease;
}

.search-box:focus-within {
  border-color: var(--color-primary);
}

.search-icon {
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.search-box input {
  flex: 1;
  min-width: 120px;
  border: none;
  background: transparent;
  outline: none;
  font-size: 14px;
  color: var(--color-text-primary);
}

.search-box input::placeholder {
  color: var(--color-text-tertiary);
}

.search-btn,
.play-btn {
  height: 32px;
  border: none;
  border-radius: var(--radius-small);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 160ms ease, color 160ms ease, opacity 160ms ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  white-space: nowrap;
}

.search-btn {
  min-width: 64px;
  padding: 0 18px;
  background: var(--color-primary);
  color: #fff;
}

.search-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.play-btn {
  padding: 0 12px;
  background: var(--color-bg-content);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
}

.play-btn:hover:not(:disabled) {
  color: var(--color-primary);
  border-color: var(--color-primary);
}

.search-btn:disabled,
.play-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error {
  margin-top: 12px;
  font-size: 13px;
  color: var(--color-primary);
}

.result-list {
  display: flex;
  flex-direction: column;
}

.loading-state,
.empty-state {
  min-height: 96px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--color-text-secondary);
  font-size: 13px;
}

@media (max-width: 720px) {
  .page {
    padding: 20px;
  }

  .search-box {
    flex-wrap: wrap;
  }

  .search-box input {
    flex-basis: calc(100% - 32px);
  }
}
</style>
