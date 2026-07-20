<template>
  <div class="page search">
    <header class="search-head">
      <h1>搜索</h1>
      <p class="hint">
        后端目前支持通过 BV 号或视频链接直接播放。输入后回车即可开始。
      </p>
      <div class="search-box">
        <AppIcon name="search" :size="18" class="search-icon" />
        <input
          v-model="input"
          type="text"
          placeholder="输入 BV 号或 bilibili.com 视频链接…"
          @keyup.enter="handlePlay"
        />
        <button class="play-btn" :disabled="!input.trim() || isLoading" @click="handlePlay">
          <LoadingDots v-if="isLoading" light />
          <span v-else>播放</span>
        </button>
      </div>
      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
    </header>

    <!-- 真实播放的结果占位：显示当前正在播放/加载的曲目 -->
    <section v-if="track" class="section">
      <SectionHeader title="正在播放" />
      <div class="result-list">
        <TrackRow
          :track="track"
          :index="0"
          :is-current="true"
          :is-playing="isPlaying"
          :is-liked="library.isLiked(track.bvid)"
          @play="player.playTrack(track!)"
          @like="library.toggleLike(track!)"
          @enqueue="player.enqueue(track!)"
        />
      </div>
    </section>

    <!-- 猜你想搜（mock）：紧凑行列表，双击播放 -->
    <section class="section">
      <SectionHeader title="猜你想搜">
        <template #extra>
          <span class="mock-tag">示例数据</span>
        </template>
      </SectionHeader>
      <div class="result-list">
        <TrackRow
          v-for="(t, i) in results"
          :key="t.bvid"
          :track="t"
          :index="i"
          :is-current="isCurrent(t.bvid)"
          :is-playing="isPlaying && isCurrent(t.bvid)"
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
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { usePlayerStore } from '@/stores/playerStore'
import { useLibraryStore } from '@/stores/libraryStore'
import { recommendTracks, hotTracks } from '@/mock/data'
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
const results = [...recommendTracks, ...hotTracks]

// 顶栏搜索框跳转过来时，用 ?q= 预填输入框
watch(
  () => route.query.q,
  (q) => {
    if (typeof q === 'string' && q) input.value = q
  },
  { immediate: true }
)

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

function isCurrent(bvid: string): boolean {
  return track.value?.bvid === bvid
}

function handlePlay() {
  if (input.value.trim()) {
    player.playInput(input.value.trim())
  }
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
  max-width: 640px;
  height: 44px;
  padding: 0 6px 0 14px;
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
  border: none;
  background: transparent;
  outline: none;
  font-size: 14px;
  color: var(--color-text-primary);
}

.search-box input::placeholder {
  color: var(--color-text-tertiary);
}

.play-btn {
  height: 32px;
  padding: 0 18px;
  border: none;
  border-radius: var(--radius-small);
  background: var(--color-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 160ms ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 60px;
}

.play-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

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

.mock-tag {
  font-size: 11px;
  color: var(--color-text-tertiary);
  padding: 2px 8px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
}
</style>
