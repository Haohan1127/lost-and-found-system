import { createRouter, createWebHistory } from 'vue-router'
import { session } from '../shared/session.js'
import { routes as claimRoutes } from '../modules/claims/routes.js'
import { routes as userRoutes } from '../modules/users/routes.js'
import DemoPage from '../demo/DemoPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // 根路径按登录状态动态跳转：已登录进演示工作台，未登录去登录页。
    { path: '/', redirect: () => (session.token ? '/demo' : '/login') },
    { path: '/demo', component: DemoPage },
    ...userRoutes,
    ...claimRoutes,
    { path: '/:pathMatch(.*)*', redirect: () => (session.token ? '/demo' : '/login') },
  ],
})
router.beforeEach(to => {
  // 受保护页面未登录 → 登录页，并把原地址放进 next 供登录后回跳。
  if (to.meta.requiresAuth && !session.token) return { path: '/login', query: { next: to.fullPath } }
})
export default router
