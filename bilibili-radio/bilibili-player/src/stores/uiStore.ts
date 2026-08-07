import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

type Theme = 'light' | 'dark'

const THEME_KEY = 'bili-radio:theme'
const LYRICS_OVERLAY_ENABLED_KEY = 'bili-radio:lyrics-overlay-enabled'
const LYRICS_OVERLAY_COLOR_KEY = 'bili-radio:lyrics-overlay-color'
const DEFAULT_LYRICS_OVERLAY_COLOR = '#fb7299'
const LYRICS_OVERLAY_COLORS = ['#fb7299', '#ffffff', '#ffd166', '#66e3ff', '#8ef08e', '#c7a6ff']

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute('data-theme', theme)
}

function detectReducedMotion(): boolean {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
}

export const useUiStore = defineStore('ui', () => {
  const stored = (localStorage.getItem(THEME_KEY) as Theme | null) ?? 'light'
  const theme = ref<Theme>(stored)
  const queueOpen = ref(false)
  const nowPlayingOpen = ref(false)
  const reducedMotion = ref(detectReducedMotion())
  const lyricsOverlayEnabled = ref(localStorage.getItem(LYRICS_OVERLAY_ENABLED_KEY) === 'true')
  const storedLyricsColor = localStorage.getItem(LYRICS_OVERLAY_COLOR_KEY)
  const lyricsOverlayColor = ref(
    storedLyricsColor && LYRICS_OVERLAY_COLORS.includes(storedLyricsColor)
      ? storedLyricsColor
      : DEFAULT_LYRICS_OVERLAY_COLOR
  )

  applyTheme(theme.value)

  watch(theme, (value) => {
    applyTheme(value)
    localStorage.setItem(THEME_KEY, value)
  })

  watch(lyricsOverlayEnabled, (value) => {
    localStorage.setItem(LYRICS_OVERLAY_ENABLED_KEY, value ? 'true' : 'false')
  })

  watch(lyricsOverlayColor, (value) => {
    localStorage.setItem(LYRICS_OVERLAY_COLOR_KEY, value)
  })

  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
  }

  function toggleQueue() {
    queueOpen.value = !queueOpen.value
  }

  function openNowPlaying() {
    nowPlayingOpen.value = true
  }

  function closeNowPlaying() {
    nowPlayingOpen.value = false
  }

  function toggleLyricsOverlay() {
    lyricsOverlayEnabled.value = !lyricsOverlayEnabled.value
  }

  function setLyricsOverlayEnabled(value: boolean) {
    lyricsOverlayEnabled.value = value
  }

  function setLyricsOverlayColor(value: string) {
    if (LYRICS_OVERLAY_COLORS.includes(value)) {
      lyricsOverlayColor.value = value
    }
  }

  return {
    theme,
    queueOpen,
    nowPlayingOpen,
    reducedMotion,
    lyricsOverlayEnabled,
    lyricsOverlayColor,
    lyricsOverlayColors: LYRICS_OVERLAY_COLORS,
    toggleTheme,
    toggleQueue,
    openNowPlaying,
    closeNowPlaying,
    toggleLyricsOverlay,
    setLyricsOverlayEnabled,
    setLyricsOverlayColor,
  }
})
