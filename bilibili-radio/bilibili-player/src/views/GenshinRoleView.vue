<template>
  <div class="role-toggle-page">
    <section class="role-toggle-state">
      <template v-if="phase === 'working'">
        <LoadingDots />
        <p>正在更新账户权限</p>
      </template>
      <template v-else-if="phase === 'done'">
        <AppIcon name="shield" :size="34" />
        <h1>{{ result?.role === 'admin' ? '已切换为管理员' : '已切换为普通用户' }}</h1>
        <p>权限已刷新，即将返回播放器。</p>
        <RouterLink to="/" class="primary-link">返回播放器</RouterLink>
      </template>
      <template v-else>
        <AppIcon name="close" :size="32" />
        <h1>权限更新失败</h1>
        <p>{{ errorMessage }}</p>
        <RouterLink to="/" class="primary-link">返回播放器</RouterLink>
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { toggleGenshinRole } from '@/api/client'
import { useAuthStore } from '@/stores/authStore'
import type { AdminRoleToggleResult } from '@/types'
import AppIcon from '@/components/base/AppIcon.vue'
import LoadingDots from '@/components/base/LoadingDots.vue'

const router = useRouter()
const auth = useAuthStore()
const phase = ref<'working' | 'done' | 'error'>('working')
const result = ref<AdminRoleToggleResult | null>(null)
const errorMessage = ref('当前账户不能执行此操作。')
let redirectTimer: ReturnType<typeof setTimeout> | null = null

onMounted(async () => {
  try {
    result.value = await toggleGenshinRole()
    await auth.initializeSession(true)
    phase.value = 'done'
    redirectTimer = setTimeout(() => {
      void router.replace({ name: 'home' })
    }, 1400)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : errorMessage.value
    phase.value = 'error'
  }
})

onBeforeUnmount(() => {
  if (redirectTimer) clearTimeout(redirectTimer)
})
</script>

<style scoped>
.role-toggle-page {
  min-height: 100%;
  display: grid;
  place-items: center;
  padding: 24px;
}

.role-toggle-state {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--color-text-secondary);
  text-align: center;
}

.role-toggle-state > .app-icon {
  color: var(--color-primary);
}

.role-toggle-state h1 {
  margin-top: 4px;
  color: var(--color-text-primary);
  font-size: 20px;
}

.role-toggle-state p {
  font-size: 13px;
}

.primary-link {
  height: 36px;
  margin-top: 8px;
  padding: 0 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-small);
  background: var(--color-primary);
  color: #fff;
  font-size: 13px;
}
</style>
