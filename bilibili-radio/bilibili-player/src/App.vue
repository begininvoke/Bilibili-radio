<template>
  <AppShell />
  <Transition name="nowplaying">
    <NowPlayingView v-if="ui.nowPlayingOpen" />
  </Transition>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { usePlayerStore } from '@/stores/playerStore'
import { useUiStore } from '@/stores/uiStore'
import AppShell from '@/components/layout/AppShell.vue'
import NowPlayingView from '@/views/NowPlayingView.vue'

const player = usePlayerStore()
const ui = useUiStore()

onMounted(() => {
  player.initialize()
})
</script>

<style>
.nowplaying-enter-active,
.nowplaying-leave-active {
  transition: opacity 260ms ease, transform 260ms ease;
}
.nowplaying-enter-from,
.nowplaying-leave-to {
  opacity: 0;
  transform: translateY(24px);
}

@media (prefers-reduced-motion: reduce) {
  .nowplaying-enter-active,
  .nowplaying-leave-active {
    transition: opacity 160ms ease;
  }
  .nowplaying-enter-from,
  .nowplaying-leave-to {
    transform: none;
  }
}
</style>
