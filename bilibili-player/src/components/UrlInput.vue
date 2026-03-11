<template>
  <div class="url-input">
    <input
      type="text"
      v-model="inputValue"
      placeholder="输入BV号或视频链接..."
      @keyup.enter="handlePlay"
      class="input-field"
    />
    <button 
      class="play-btn" 
      @click="handlePlay"
      :disabled="isLoading"
    >
      {{ isLoading ? '加载中...' : '播放' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { usePlayerStore } from '@/stores/playerStore'
import { storeToRefs } from 'pinia'

const store = usePlayerStore()
const { isLoading } = storeToRefs(store)
const { playVideo } = store

const inputValue = ref('')

function handlePlay() {
  if (inputValue.value.trim()) {
    playVideo(inputValue.value.trim())
  }
}
</script>

<style scoped>
.url-input {
  display: flex;
  gap: 8px;
  width: 100%;
}

.input-field {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  font-size: 13px;
  outline: none;
  transition: all 0.2s ease;
}

.input-field::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.input-field:focus {
  border-color: rgba(0, 199, 214, 0.5);
  background: rgba(255, 255, 255, 0.08);
}

.play-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #00c7d6, #00e5ff);
  color: #000;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.play-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 199, 214, 0.4);
}

.play-btn:active:not(:disabled) {
  transform: translateY(0);
}

.play-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
