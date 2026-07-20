<template>
  <header class="topbar">
    <div class="nav-arrows">
      <button class="icon-btn" title="后退" @click="goBack">
        <AppIcon name="chevron" :size="18" style="transform: rotate(90deg)" />
      </button>
      <button class="icon-btn" title="前进" @click="goForward">
        <AppIcon name="chevron" :size="18" style="transform: rotate(-90deg)" />
      </button>
    </div>

    <form class="search-box" @submit.prevent="submitSearch">
      <AppIcon name="search" :size="16" class="search-icon" />
      <input
        v-model="keyword"
        type="text"
        placeholder="搜索，或粘贴 BV号 / 视频链接"
        class="search-input"
      />
    </form>

    <div class="actions">
      <button class="icon-btn" :title="isDark ? '切换到浅色' : '切换到深色'" @click="ui.toggleTheme">
        <AppIcon :name="isDark ? 'sun' : 'moon'" :size="18" />
      </button>
      <button class="icon-btn" title="消息">
        <AppIcon name="bell" :size="18" />
      </button>
      <button class="avatar" title="登录">
        <span class="avatar-fallback">登录</span>
      </button>

      <div class="win-buttons">
        <span class="win-dot min" />
        <span class="win-dot max" />
        <span class="win-dot close" />
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUiStore } from '@/stores/uiStore'
import AppIcon from '@/components/base/AppIcon.vue'

const router = useRouter()
const ui = useUiStore()

const keyword = ref('')
const isDark = computed(() => ui.theme === 'dark')

function submitSearch() {
  const q = keyword.value.trim()
  if (!q) return
  router.push({ name: 'search', query: { q } })
}

function goBack() {
  router.back()
}

function goForward() {
  router.forward()
}
</script>

<style scoped>
.topbar {
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 20px;
  background: var(--color-bg-content);
  border-bottom: 1px solid var(--color-border);
}

.nav-arrows {
  display: flex;
  gap: 4px;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  border-radius: 50%;
  cursor: pointer;
  transition: background 160ms ease, color 160ms ease;
}

.icon-btn:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 320px;
  max-width: 40%;
  height: 36px;
  padding: 0 14px;
  background: var(--color-bg-app);
  border: 1px solid transparent;
  border-radius: 999px;
  transition: border-color 160ms ease, background 160ms ease;
}

.search-box:focus-within {
  border-color: var(--color-primary);
  background: var(--color-bg-content);
}

.search-icon {
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: 13px;
  color: var(--color-text-primary);
}

.search-input::placeholder {
  color: var(--color-text-tertiary);
}

.actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.avatar {
  height: 32px;
  padding: 0 14px;
  border: 1px solid var(--color-border);
  background: transparent;
  border-radius: 999px;
  color: var(--color-text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: border-color 160ms ease, color 160ms ease;
}

.avatar:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.win-buttons {
  display: flex;
  gap: 8px;
  margin-left: 8px;
  padding-left: 12px;
  border-left: 1px solid var(--color-border);
}

.win-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  cursor: pointer;
}

.win-dot.min { background: #febc2e; }
.win-dot.max { background: #28c840; }
.win-dot.close { background: #ff5f57; }
</style>
