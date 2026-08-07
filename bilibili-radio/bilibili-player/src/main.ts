import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { initializeDesktopRuntime } from './desktop/runtime'
import './styles/tokens.css'
import './styles/global.css'

async function bootstrap() {
  await initializeDesktopRuntime()

  const app = createApp(App)
  const pinia = createPinia()

  app.use(pinia)
  app.use(router)
  app.mount('#app')
}

void bootstrap()
