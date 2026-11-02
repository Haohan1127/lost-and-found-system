import { createRouter, createWebHistory } from 'vue-router'
import { session } from '../shared/session.js'
import { routes as claimRoutes } from '../modules/claims/routes.js'
import DemoPage from '../demo/DemoPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/demo' },
    { path: '/demo', component: DemoPage },
    ...claimRoutes,
    { path: '/:pathMatch(.*)*', redirect: '/demo' },
  ],
})
router.beforeEach(to => {
  if (to.meta.requiresAuth && !session.token) return { path: '/demo', query: { next: to.fullPath } }
})
export default router
