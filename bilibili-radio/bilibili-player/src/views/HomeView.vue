<template>
  <div class="page home">
    <header class="welcome">
      <h1>{{ greeting }}</h1>
      <p class="sub">继续听上次没播完的内容</p>
    </header>

    <section v-if="recent.length" class="section">
      <SectionHeader title="最近播放">
        <template #extra>
          <RouterLink to="/recent" class="more-link">查看全部</RouterLink>
        </template>
      </SectionHeader>
      <div class="card-grid">
        <TrackCard
          v-for="track in recent.slice(0, 5)"
          :key="track.trackId ?? track.bvid"
          :track="track"
          @play="player.playTrack(track)"
        />
      </div>
    </section>

    <section class="section">
      <SectionHeader title="为你推荐" />
      <p class="pending-text">目前正在开发中，请您看看其他内容。</p>
    </section>

    <section class="section">
      <SectionHeader title="我的播放次数 Top 10" :count="playCountRanking.length" />
      <div v-if="playCountRanking.length" class="rank-list">
        <button
          v-for="(track, i) in playCountRanking"
          :key="track.trackId ?? `${track.bvid}:${track.cid ?? i}`"
          class="rank-row"
          @click="player.playTrack(track)"
        >
          <span class="rank-index">{{ i + 1 }}</span>
          <img class="rank-cover" :src="mediaUrl(track.cover)" :alt="track.title" loading="lazy" />
          <span class="rank-title" :title="track.title">{{ track.title }}</span>
          <span class="rank-owner">{{ track.owner }}</span>
          <span class="rank-count">已播放 {{ formatCount(track.recentPlayCount ?? 0) }} 次</span>
        </button>
      </div>
      <p v-else class="empty-text">暂无播放次数数据，先搜索或播放几首内容。</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { storeToRefs } from 'pinia'
import { mediaUrl } from '@/api/client'
import { usePlayerStore } from '@/stores/playerStore'
import { useLibraryStore } from '@/stores/libraryStore'
import type { Track } from '@/types'
import { formatCount } from '@/utils/format'
import TrackCard from '@/components/TrackCard.vue'
import SectionHeader from '@/components/base/SectionHeader.vue'

const player = usePlayerStore()
const library = useLibraryStore()
const { recent } = storeToRefs(library)

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 12) return '上午好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const playCountRanking = computed(() => {
  return uniqueTracks(recent.value)
    .filter((track) => Number.isFinite(track.recentPlayCount) && (track.recentPlayCount ?? 0) > 0)
    .sort((a, b) => (b.recentPlayCount ?? 0) - (a.recentPlayCount ?? 0))
    .slice(0, 10)
})

function uniqueTracks(tracks: Track[]): Track[] {
  const map = new Map<string, Track>()
  for (const track of tracks) {
    const key = track.trackId ?? `${track.bvid}:${track.cid ?? 'video'}`
    if (!map.has(key)) map.set(key, track)
  }
  return [...map.values()]
}

</script>

<style scoped>
.page {
  padding: 24px 32px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.welcome h1 {
  font-size: 26px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.welcome .sub {
  margin-top: 6px;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 20px;
}

.pending-text,
.empty-text {
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.rank-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.rank-row {
  display: grid;
  grid-template-columns: 32px 44px minmax(0, 1fr) minmax(96px, 160px) 112px;
  align-items: center;
  gap: 12px;
  height: 58px;
  padding: 0 12px;
  border: none;
  border-radius: var(--radius-small);
  background: transparent;
  color: var(--color-text-primary);
  cursor: pointer;
  text-align: left;
  transition: background 160ms ease;
}

.rank-row:hover {
  background: var(--color-bg-hover);
}

.rank-index {
  color: var(--color-primary);
  font-weight: 700;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.rank-cover {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-small);
  object-fit: cover;
  background: var(--color-bg-hover);
}

.rank-title,
.rank-owner {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.rank-title {
  font-size: 14px;
}

.rank-owner,
.rank-count {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.rank-count {
  text-align: right;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.more-link {
  font-size: 13px;
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: color 160ms ease;
}

.more-link:hover {
  color: var(--color-primary);
}

@media (max-width: 720px) {
  .page {
    padding: 20px;
  }

  .rank-row {
    grid-template-columns: 28px 40px minmax(0, 1fr) 96px;
  }

  .rank-owner {
    display: none;
  }
}
</style>
