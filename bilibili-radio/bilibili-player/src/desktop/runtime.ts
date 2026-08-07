import { configureApiBaseUrl } from '@/api/client'

const DEFAULT_DESKTOP_API_BASE_URL = 'http://127.0.0.1:41517'

export async function initializeDesktopRuntime(): Promise<void> {
  try {
    const { invoke } = await import('@tauri-apps/api/core')
    const endpoint = await invoke<string>('desktop_backend_endpoint')
    configureApiBaseUrl(endpoint)
  } catch {
    configureApiBaseUrl(resolveDesktopFallbackEndpoint())
  }
}

function resolveDesktopFallbackEndpoint(): string | null {
  const protocol = window.location.protocol
  const host = window.location.hostname
  const isDesktopHost = host === 'tauri.localhost' || protocol === 'tauri:'
  return isDesktopHost ? DEFAULT_DESKTOP_API_BASE_URL : null
}
