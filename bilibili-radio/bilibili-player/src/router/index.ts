import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'

if (window.location.pathname === '/admin/genshin' && !window.location.hash) {
  window.history.replaceState(null, '', `/#/admin/genshin${window.location.search}`)
}

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/session-unavailable',
      name: 'session-unavailable',
      component: () => import('@/views/SessionUnavailableView.vue'),
      meta: { layout: 'auth', sessionRecovery: true },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { layout: 'auth' },
    },
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
    },
    {
      path: '/search',
      name: 'search',
      component: () => import('@/views/SearchView.vue'),
    },
    {
      path: '/favorites',
      name: 'favorites',
      component: () => import('@/views/FavoritesView.vue'),
    },
    {
      path: '/playlist/:id',
      name: 'playlist',
      component: () => import('@/views/PlaylistDetailView.vue'),
    },
    {
      path: '/recent',
      name: 'recent',
      component: () => import('@/views/RecentView.vue'),
    },
    {
      path: '/likes',
      name: 'likes',
      component: () => import('@/views/LikesView.vue'),
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/views/AdminView.vue'),
      meta: { requiresAdmin: true },
    },
    {
      path: '/admin/genshin',
      name: 'admin-genshin',
      component: () => import('@/views/GenshinRoleView.vue'),
    },
    {
      path: '/desktop-lyrics',
      name: 'desktop-lyrics',
      component: () => import('@/views/DesktopLyricsOverlayView.vue'),
      meta: { layout: 'overlay', desktopOverlay: true },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach(async (to) => {
  if (to.meta.desktopOverlay) return true
  if (to.meta.sessionRecovery) return true

  const auth = useAuthStore()
  try {
    await auth.initializeSession()
  } catch {
    return {
      name: 'session-unavailable',
      query: { redirect: to.fullPath },
    }
  }

  if (!auth.appAuthenticated) {
    auth.loginWithOidc()
    return false
  }

  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { name: 'home', query: { denied: 'admin' } }
  }

  return true
})

export default router
