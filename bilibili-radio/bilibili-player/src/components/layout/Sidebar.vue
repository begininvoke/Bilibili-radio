<template>
  <aside class="sidebar">
    <div class="brand">
      <img class="brand-logo" :src="iconUrl" alt="logo" />
      <div class="brand-name">
        <span class="brand-title">B站电台</span>
        <span class="brand-sub">bilibili radio</span>
      </div>
    </div>

    <nav class="nav">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        :class="{ active: isActive(item.to) }"
      >
        <span class="indicator" />
        <AppIcon :name="item.icon" :size="18" />
        <span class="nav-label">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div class="nav-section-title">我的音乐</div>
    <nav class="nav">
      <RouterLink to="/likes" class="nav-item" :class="{ active: isActive('/likes') }">
        <span class="indicator" />
        <AppIcon name="heart" :size="18" />
        <span class="nav-label">我喜欢</span>
      </RouterLink>
      <RouterLink to="/recent" class="nav-item" :class="{ active: isActive('/recent') }">
        <span class="indicator" />
        <AppIcon name="clock" :size="18" />
        <span class="nav-label">最近播放</span>
      </RouterLink>
    </nav>

    <div class="nav-section-title playlists-title">
      <span>本地歌单</span>
      <button class="add-playlist" title="新建歌单" @click="createPlaylist">
        <AppIcon name="plus" :size="16" />
      </button>
    </div>
    <nav class="nav playlists">
      <RouterLink
        v-for="pl in library.playlists"
        :key="pl.id"
        :to="`/playlist/${pl.id}`"
        class="nav-item"
        :class="{ active: isActive(`/playlist/${pl.id}`) }"
      >
        <span class="indicator" />
        <AppIcon name="list" :size="18" />
        <span class="nav-label">{{ pl.name }}</span>
      </RouterLink>
      <p v-if="library.playlists.length === 0" class="no-playlist">还没有歌单，点上方 + 新建</p>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router'
import { useLibraryStore } from '@/stores/libraryStore'
import AppIcon from '@/components/base/AppIcon.vue'
import iconUrl from '@/assets/icon.png'

const route = useRoute()
const library = useLibraryStore()

const navItems = [
  { to: '/', label: '发现', icon: 'home' },
  { to: '/search', label: '搜索', icon: 'search' },
  { to: '/favorites', label: 'B站收藏夹', icon: 'star' },
]

function isActive(path: string): boolean {
  if (path === '/') return route.path === '/'
  return route.path === path || route.path.startsWith(path + '/')
}

function createPlaylist() {
  const name = window.prompt('新歌单名称', '我的歌单')
  if (name && name.trim()) {
    library.createPlaylist(name.trim())
  }
}
</script>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  height: 100%;
  background: var(--color-bg-sidebar);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  padding: 16px 12px;
  overflow-y: auto;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 8px 20px;
}

.brand-logo {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  object-fit: cover;
}

.brand-name {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.brand-sub {
  font-size: 11px;
  color: var(--color-text-tertiary);
  letter-spacing: 0.5px;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  height: 40px;
  padding: 0 12px;
  border-radius: var(--radius-small);
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: background 160ms ease, color 160ms ease;
}

.nav-item:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.nav-item.active {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 0;
  border-radius: 0 2px 2px 0;
  background: var(--color-primary);
  transition: height 160ms ease;
}

.nav-item.active .indicator {
  height: 18px;
}

.nav-label {
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav-section-title {
  font-size: 12px;
  color: var(--color-text-tertiary);
  padding: 20px 12px 8px;
  font-weight: 500;
}

.playlists-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.add-playlist {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: none;
  background: transparent;
  color: var(--color-text-tertiary);
  border-radius: 6px;
  cursor: pointer;
  transition: background 160ms ease, color 160ms ease;
}

.add-playlist:hover {
  background: var(--color-bg-hover);
  color: var(--color-primary);
}

.playlists {
  flex: 1;
}

.no-playlist {
  font-size: 12px;
  color: var(--color-text-tertiary);
  padding: 8px 12px;
  line-height: 1.5;
}
</style>
