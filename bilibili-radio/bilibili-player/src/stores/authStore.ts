import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  createBiliLoginQr,
  fetchAuthStatus,
  logoutBili,
  pollBiliLoginQr,
} from '@/api/client'
import type { AuthQrCode, AuthQrStatus, AuthStatus, BiliUserProfile } from '@/types'

function readLoginRequired(): boolean {
  const value = import.meta.env.VITE_REQUIRE_BILI_LOGIN
  if (value == null || value === '') return import.meta.env.PROD
  return !['0', 'false', 'off', 'no'].includes(String(value).toLowerCase())
}

const defaultStatus: AuthStatus = {
  qrLoginEnabled: true,
  isLoggedIn: false,
  user: null,
  cookieUpdatedAt: null,
}

export const useAuthStore = defineStore('auth', () => {
  const loginRequired = readLoginRequired()
  const status = ref<AuthStatus>(defaultStatus)
  const qrCode = ref<AuthQrCode | null>(null)
  const qrStatus = ref<AuthQrStatus | null>(null)
  const isChecking = ref(false)
  const isQrLoading = ref(false)
  const errorMessage = ref<string | null>(null)
  const hasLoaded = ref(false)

  let statusPromise: Promise<AuthStatus> | null = null

  const isLoggedIn = computed(() => status.value.isLoggedIn)
  const user = computed<BiliUserProfile | null>(() => status.value.user)

  async function initialize(refresh = false): Promise<AuthStatus> {
    if (hasLoaded.value && !refresh) return status.value
    if (statusPromise) return statusPromise

    isChecking.value = true
    errorMessage.value = null
    statusPromise = fetchAuthStatus(refresh)
      .then((data) => {
        status.value = data
        hasLoaded.value = true
        return data
      })
      .catch((error) => {
        status.value = defaultStatus
        hasLoaded.value = true
        errorMessage.value = error instanceof Error ? error.message : '登录状态检查失败'
        return status.value
      })
      .finally(() => {
        isChecking.value = false
        statusPromise = null
      })
    return statusPromise
  }

  async function startQrLogin(): Promise<AuthQrCode> {
    isQrLoading.value = true
    errorMessage.value = null
    qrStatus.value = null
    try {
      qrCode.value = await createBiliLoginQr()
      return qrCode.value
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '二维码生成失败'
      throw error
    } finally {
      isQrLoading.value = false
    }
  }

  async function pollQrLogin(): Promise<AuthQrStatus | null> {
    if (!qrCode.value) return null
    try {
      const nextStatus = await pollBiliLoginQr(qrCode.value.qrcodeKey)
      qrStatus.value = nextStatus
      if (nextStatus.status === 'confirmed') {
        status.value = {
          qrLoginEnabled: true,
          isLoggedIn: true,
          user: nextStatus.user,
          cookieUpdatedAt: new Date().toISOString(),
        }
        hasLoaded.value = true
      }
      return nextStatus
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '扫码状态检查失败'
      return null
    }
  }

  async function logout() {
    await logoutBili()
    status.value = defaultStatus
    qrCode.value = null
    qrStatus.value = null
    hasLoaded.value = true
  }

  return {
    loginRequired,
    status,
    qrCode,
    qrStatus,
    isChecking,
    isQrLoading,
    errorMessage,
    hasLoaded,
    isLoggedIn,
    user,
    initialize,
    startQrLogin,
    pollQrLogin,
    logout,
  }
})
