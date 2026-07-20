<template>
  <div class="page home">
    <header class="welcome">
      <h1>{{ greeting }}</h1>
      <p class="sub">继续看看上次的内容吧</p>
    </header>

    <!-- 继续播放 / 最近播放 快捷入口 -->
    <section v-if="recent.length" class="section">
      <SectionHeader title="最近播放">
        <template #extra>
          <RouterLink to="/recent" class="more-link">查看全部</RouterLink>
        </template>
      </SectionHeader>
      <div class="card-grid">
        <TrackCard
          v-for="t in recent.slice(0, 5)"
          :key="t.bvid"
          :track="t"
          @play="player.playTrack(t)"
        />
      </div>
    </section>

    <!-- 收藏夹快捷入口 -->
    <section class="section">
      <SectionHeader title="B站收藏夹">
        <template #extra>
          <RouterLink to="/favorites" class="more-link">全部收藏夹</RouterLink>
        </template>
      </SectionHeader>
      <div class="fav-grid">
        <RouterLink
          v-for="f in favoriteFolders"
          :key="f.id"
          :to="`/favorites?folder=${f.id}`"
          class="fav-entry"
        >
          <img :src="f.cover" :alt="f.title" loading="lazy" />
          <div class="fav-info">
            <span class="fav-title">{{ f.title }}</span>
            <span class="fav-count">{{ f.count }} 个内容</span>
          </div>
        </RouterLink>
      </div>
    </section>

    <!-- 为你推荐 -->
    <section class="section">
      <SectionHeader title="为你推荐" />
      <div class="card-grid">
        <TrackCard
          v-for="t in recommendTracks"
          :key="t.bvid"
          :track="t"
          @play="player.playTrack(t)"
        />
      </div>
    </section>

    <!-- 热门视频 -->
    <section class="section">
      <SectionHeader title="热门视频" />
      <div class="card-grid">
        <TrackCard
          v-for="t in hotTracks"
          :key="t.bvid"
          :track="t"
          @play="player.playTrack(t)"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { storeToRefs } from 'pinia'
import { usePlayerStore } from '@/stores/playerStore'
import { useLibraryStore } from '@/stores/libraryStore'
import { recommendTracks, hotTracks, favoriteFolders } from '@/mock/data'
import TrackCard from '@/components/TrackCard.vue'
import SectionHeader from '@/components/base/SectionHeader.vue'

const player = usePlayerStore()
const library = useLibraryStore()
const { recent } = storeToRefs(library)

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})
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

.fav-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.fav-entry {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border-radius: var(--radius-medium);
  text-decoration: none;
  transition: background 160ms ease;
}

.fav-entry:hover {
  background: var(--color-bg-hover);
}

.fav-entry img {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-small);
  object-fit: cover;
  flex-shrink: 0;
}

.fav-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.fav-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fav-count {
  font-size: 12px;
  color: var(--color-text-tertiary);
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
</style>
