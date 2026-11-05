// 成员 A 的四条页面路由；meta.requiresAuth 交由 router/index.js 的守卫统一处理。
export const routes = [
  { path: '/login', component: () => import('./pages/LoginPage.vue') },
  { path: '/register', component: () => import('./pages/RegisterPage.vue') },
  { path: '/me/profile', component: () => import('./pages/ProfilePage.vue'), meta: { requiresAuth: true } },
  { path: '/me/campus-binding', component: () => import('./pages/CampusBindingPage.vue'), meta: { requiresAuth: true } },
]
