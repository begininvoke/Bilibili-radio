<template>
  <div class="app-shell">
    <Sidebar class="shell-sidebar" />
    <TopBar class="shell-topbar" />
    <main class="shell-content">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>
    <PlayerBar class="shell-player" />
    <QueueDrawer />
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import Sidebar from '@/components/layout/Sidebar.vue'
import TopBar from '@/components/layout/TopBar.vue'
import PlayerBar from '@/components/layout/PlayerBar.vue'
import QueueDrawer from '@/components/layout/QueueDrawer.vue'
</script>

<style scoped>
.app-shell {
  width: 100vw;
  height: 100vh;
  display: grid;
  grid-template-columns: var(--sidebar-width) 1fr;
  grid-template-rows: var(--topbar-height) 1fr var(--player-height);
  grid-template-areas:
    'sidebar topbar'
    'sidebar content'
    'player player';
  background: var(--color-bg-app);
  overflow: hidden;
}

.shell-sidebar {
  grid-area: sidebar;
}

.shell-topbar {
  grid-area: topbar;
}

.shell-content {
  grid-area: content;
  overflow-y: auto;
  background: var(--color-bg-app);
}

.shell-player {
  grid-area: player;
}

/* 页面切换过渡 */
.page-enter-active,
.page-leave-active {
  transition: opacity 180ms ease;
}
.page-enter-from,
.page-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .page-enter-active,
  .page-leave-active {
    transition: none;
  }
}
</style>
