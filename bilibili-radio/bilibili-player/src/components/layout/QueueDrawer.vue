<template>
  <Teleport to="body">
    <Transition name="drawer-fade">
      <div v-if="ui.queueOpen" class="drawer-mask" @click="ui.toggleQueue()" />
    </Transition>
    <Transition name="drawer-slide">
      <aside v-if="ui.queueOpen" class="queue-drawer">
        <header class="drawer-header">
          <div class="drawer-title">
            <span>播放队列</span>
            <span class="count">{{ player.queue.length }}</span>
          </div>
          <div class="drawer-actions">
            <button
              class="text-btn"
              :disabled="player.queue.length === 0"
              @click="player.clearQueue()"
            >
              清空
            </button>
            <button class="icon-btn" title="关闭" @click="ui.toggleQueue()">
              <AppIcon name="close" :size="18" />
            </button>
          </div>
        </header>

        <div class="drawer-body">
          <ul v-if="player.queue.length > 0" class="queue-list">
            <li
              v-for="(item, i) in player.queue"
              :key="item.trackId ?? `${item.bvid}:${item.cid ?? i}`"
              class="queue-item"
              :class="{ active: i === player.currentIndex }"
              @dblclick="player.playAt(i)"
            >
              <div class="q-index">
                <PlayingBars v-if="i === player.currentIndex && player.isPlaying" />
                <span v-else>{{ i + 1 }}</span>
              </div>
              <div class="q-main" @click="player.playAt(i)">
                <div class="q-title" :class="{ current: i === player.currentIndex }" :title="item.title">
                  {{ item.title }}
                </div>
                <div class="q-owner">{{ item.owner }}</div>
              </div>
              <span class="q-duration">{{ formatDuration(item.duration) }}</span>
              <button class="q-remove" title="从队列移除" @click.stop="player.removeFromQueue(i)">
                <AppIcon name="close" :size="14" />
              </button>
            </li>
          </ul>

          <EmptyState
            v-else
            title="队列还是空的"
            description="在搜索或收藏夹里双击一首，就会出现在这里"
          />
        </div>
      </aside>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { usePlayerStore } from '@/stores/playerStore'
import { useUiStore } from '@/stores/uiStore'
import { formatDuration } from '@/utils/format'
import AppIcon from '@/components/base/AppIcon.vue'
import PlayingBars from '@/components/base/PlayingBars.vue'
import EmptyState from '@/components/base/EmptyState.vue'

const player = usePlayerStore()
const ui = useUiStore()
</script>

<style scoped>
.drawer-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.28);
  z-index: 40;
}

.queue-drawer {
  position: fixed;
  top: 0;
  right: 0;
  width: var(--queue-width);
  height: calc(100vh - var(--player-height));
  background: var(--color-bg-content);
  border-left: 1px solid var(--color-border);
  box-shadow: var(--shadow-popup);
  z-index: 41;
  display: flex;
  flex-direction: column;
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px 14px;
  border-bottom: 1px solid var(--color-border);
}

.drawer-title {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.count {
  font-size: 12px;
  color: var(--color-text-tertiary);
  font-weight: 400;
}

.drawer-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.text-btn {
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 13px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-small);
  transition: background 160ms ease, color 160ms ease;
}

.text-btn:hover:not(:disabled) {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.text-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.icon-btn {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  border-radius: 50%;
  cursor: pointer;
  transition: background 160ms ease;
}

.icon-btn:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.queue-list {
  list-style: none;
}

.queue-item {
  display: grid;
  grid-template-columns: 28px 1fr auto 24px;
  align-items: center;
  gap: 10px;
  height: 56px;
  padding: 0 10px;
  border-radius: var(--radius-small);
  cursor: default;
  transition: background 160ms ease;
}

.queue-item:hover {
  background: var(--color-bg-hover);
}

.queue-item.active {
  background: var(--color-primary-soft);
}

.q-index {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--color-text-tertiary);
  font-variant-numeric: tabular-nums;
}

.q-main {
  min-width: 0;
  cursor: pointer;
}

.q-title {
  font-size: 13px;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.q-title.current {
  color: var(--color-primary);
}

.q-owner {
  font-size: 11px;
  color: var(--color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 2px;
}

.q-duration {
  font-size: 12px;
  color: var(--color-text-tertiary);
  font-variant-numeric: tabular-nums;
}

.q-remove {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--color-text-tertiary);
  border-radius: 50%;
  cursor: pointer;
  opacity: 0;
  transition: opacity 160ms ease, background 160ms ease;
}

.queue-item:hover .q-remove {
  opacity: 1;
}

.q-remove:hover {
  background: var(--color-bg-hover);
  color: var(--color-primary);
}

/* 过渡 */
.drawer-fade-enter-active,
.drawer-fade-leave-active {
  transition: opacity 200ms ease;
}
.drawer-fade-enter-from,
.drawer-fade-leave-to {
  opacity: 0;
}

.drawer-slide-enter-active,
.drawer-slide-leave-active {
  transition: transform 240ms cubic-bezier(0.22, 1, 0.36, 1);
}
.drawer-slide-enter-from,
.drawer-slide-leave-to {
  transform: translateX(100%);
}

@media (prefers-reduced-motion: reduce) {
  .drawer-slide-enter-active,
  .drawer-slide-leave-active,
  .drawer-fade-enter-active,
  .drawer-fade-leave-active {
    transition: none;
  }
}
</style>
