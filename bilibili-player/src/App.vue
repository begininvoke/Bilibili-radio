<template>
  <div class="app-wrapper">
    <div class="background-layer"></div>
    <div class="blur-overlay"></div>
    
    <div class="app-container" :class="{ 'window-draggable': isWindowDraggable }">
      <div class="decorative-texts">
        <div class="deco-text deco-left-1">八千年、ずっと泣きたかったんだよね。</div>
        <div class="deco-text deco-right-1">一期一会</div>
        <div class="deco-text deco-left-2">我不会遵从你们的结局，那根本不是我想要的</div>
        <div class="deco-text deco-right-2">我们不会遵从别人写下的故事，这里只有你和我</div>
      </div>
      
      <div class="main-title-group">
        <div class="main-title title-line-1">我会找到逆转时间的公式</div>
        <div class="main-title title-line-2">跨越八千年，我依然会找到你</div>
        <div class="main-title title-line-3">在这个宇宙中，我永远爱着你</div>
      </div>
      
      <div class="player-card">
        <div class="window-header">
          <div class="window-title">
            <span class="title-icon">✨</span>
            <span class="title-text">B站后台播放器</span>
          </div>
          <div class="connection-status" :class="{ connected: isConnected }">
            {{ isConnected ? '已连接' : '未连接' }}
          </div>
        </div>

        <div class="main-content">
          <UrlInput />
          
          <VideoInfo v-if="videoInfo" />
          
          <ProgressBar />
          
          <div class="controls-row">
            <PlayerControls />
            <VolumeControl />
          </div>
          
          <StatusDisplay />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { usePlayerStore } from '@/stores/playerStore'
import { storeToRefs } from 'pinia'

import UrlInput from '@/components/UrlInput.vue'
import VideoInfo from '@/components/VideoInfo.vue'
import ProgressBar from '@/components/ProgressBar.vue'
import PlayerControls from '@/components/PlayerControls.vue'
import VolumeControl from '@/components/VolumeControl.vue'
import StatusDisplay from '@/components/StatusDisplay.vue'

const store = usePlayerStore()
const { isConnected, videoInfo } = storeToRefs(store)

const isWindowDraggable = ref(false)

onMounted(async () => {
  await store.initialize()
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  background: transparent !important;
  overflow: hidden;
  width: 100%;
  height: 100%;
}

#app {
  background: transparent;
  width: 100%;
  height: 100%;
}
</style>

<style scoped>
.app-wrapper {
  width: 100vw;
  height: 100vh;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.background-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image: url('./icon/theme.jpg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  z-index: 0;
}

.blur-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  backdrop-filter: blur(5px);
  background: linear-gradient(
    135deg,
    rgba(138, 43, 226, 0.3) 0%,
    rgba(255, 105, 180, 0.3) 50%,
    rgba(186, 85, 211, 0.3) 100%
  );
  z-index: 1;
}

.app-container {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  gap: 20px;
  -webkit-app-region: no-drag;
}

.window-draggable {
  -webkit-app-region: drag;
}

.decorative-texts {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.deco-text {
  position: absolute;
  font-family: 'ZCOOL KuaiLe', 'Noto Sans JP', cursive;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
  text-shadow: 
    0 0 10px rgba(255, 105, 180, 0.5),
    0 0 20px rgba(138, 43, 226, 0.3);
  white-space: nowrap;
  animation: float 6s ease-in-out infinite;
}

.deco-left-1 {
  top: 15%;
  left: 5%;
  animation-delay: 0s;
}

.deco-right-1 {
  top: 25%;
  right: 5%;
  animation-delay: 1s;
}

.deco-left-2 {
  bottom: 25%;
  left: 8%;
  animation-delay: 2s;
}

.deco-right-2 {
  bottom: 15%;
  right: 5%;
  animation-delay: 3s;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.main-title-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  z-index: 2;
}

.main-title {
  font-family: 'Noto Sans JP', 'ZCOOL KuaiLe', sans-serif;
  font-size: 22px;
  font-weight: 700;
  text-align: center;
  background: linear-gradient(
    90deg,
    #e879f9 0%,
    #f0abfc 25%,
    #ffffff 50%,
    #f0abfc 75%,
    #e879f9 100%
  );
  background-size: 200% auto;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: none;
  filter: drop-shadow(0 0 15px rgba(232, 121, 249, 0.6))
          drop-shadow(0 0 30px rgba(168, 85, 247, 0.4));
  animation: shimmer 3s linear infinite, titleFloat 4s ease-in-out infinite;
  cursor: default;
  transition: transform 0.3s ease;
}

.main-title:hover {
  transform: scale(1.05);
}

.title-line-1 {
  animation-delay: 0s;
}

.title-line-2 {
  animation-delay: 0.5s;
}

.title-line-3 {
  animation-delay: 1s;
}

@keyframes shimmer {
  0% {
    background-position: 200% center;
  }
  100% {
    background-position: -200% center;
  }
}

@keyframes titleFloat {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-5px);
  }
}

.player-card {
  width: 380px;
  background: rgba(30, 20, 50, 0.75);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  box-shadow: 
    0 8px 32px rgba(138, 43, 226, 0.3),
    0 0 60px rgba(255, 105, 180, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  overflow: hidden;
  font-family: 'Noto Sans JP', -apple-system, BlinkMacSystemFont, sans-serif;
  z-index: 2;
}

.window-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(
    90deg,
    rgba(138, 43, 226, 0.2) 0%,
    rgba(255, 105, 180, 0.2) 100%
  );
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  -webkit-app-region: drag;
}

.window-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  font-size: 16px;
  animation: sparkle 2s ease-in-out infinite;
}

@keyframes sparkle {
  0%, 100% {
    transform: scale(1) rotate(0deg);
    filter: brightness(1);
  }
  50% {
    transform: scale(1.2) rotate(10deg);
    filter: brightness(1.3);
  }
}

.title-text {
  font-size: 13px;
  font-weight: 500;
  background: linear-gradient(90deg, #e879f9, #f0abfc);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.connection-status {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 12px;
  background: rgba(255, 107, 107, 0.2);
  color: #ff6b9d;
  transition: all 0.3s ease;
  border: 1px solid rgba(255, 107, 157, 0.3);
}

.connection-status.connected {
  background: rgba(232, 121, 249, 0.2);
  color: #e879f9;
  border-color: rgba(232, 121, 249, 0.4);
  box-shadow: 0 0 10px rgba(232, 121, 249, 0.3);
}

.main-content {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  -webkit-app-region: no-drag;
}

.controls-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
