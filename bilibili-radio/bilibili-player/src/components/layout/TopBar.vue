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
        placeholder="搜索，或粘贴 BV / 视频链接"
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
      <button class="avatar" :title="authTitle" @click="openLogin">
        <img v-if="auth.user?.face" class="avatar-img" :src="mediaUrl(auth.user.face)" :alt="auth.user.name" />
        <span class="avatar-fallback">{{ auth.user?.name || '登录' }}</span>
      </button>

    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import { useUiStore } from '@/stores/uiStore'
import { mediaUrl } from '@/api/client'
import AppIcon from '@/components/base/AppIcon.vue'

const router = useRouter()
const ui = useUiStore()
const auth = useAuthStore()

const keyword = ref('')
const isDark = computed(() => ui.theme === 'dark')
const authTitle = computed(() => (auth.isLoggedIn ? `已登录：${auth.user?.name ?? ''}` : '登录 B 站'))

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

function openLogin() {
  router.push({ name: 'login' })
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
  max-width: 132px;
  min-width: 64px;
  padding: 0 12px 0 6px;
  border: 1px solid var(--color-border);
  background: transparent;
  border-radius: 999px;
  color: var(--color-text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: border-color 160ms ease, color 160ms ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.avatar:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.avatar-img {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.avatar-fallback {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

</style>
