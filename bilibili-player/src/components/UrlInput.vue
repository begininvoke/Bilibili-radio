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
  border: 1px solid rgba(232, 121, 249, 0.3);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  font-size: 13px;
  outline: none;
  transition: all 0.3s ease;
  font-family: 'Noto Sans JP', sans-serif;
}

.input-field::placeholder {
  color: rgba(232, 121, 249, 0.5);
}

.input-field:focus {
  border-color: rgba(232, 121, 249, 0.6);
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 
    0 0 15px rgba(232, 121, 249, 0.2),
    inset 0 0 10px rgba(168, 85, 247, 0.1);
}

.play-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #a855f7, #e879f9);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
  box-shadow: 0 0 15px rgba(168, 85, 247, 0.4);
  font-family: 'Noto Sans JP', sans-serif;
}

.play-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 
    0 4px 20px rgba(168, 85, 247, 0.6),
    0 0 30px rgba(232, 121, 249, 0.4);
  background: linear-gradient(135deg, #c084fc, #f0abfc);
}

.play-btn:active:not(:disabled) {
  transform: translateY(0);
}

.play-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
}
</style>
