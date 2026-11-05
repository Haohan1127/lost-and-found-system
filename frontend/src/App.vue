<script setup>
import { watch, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { session, clearSession } from './shared/session.js'
import { request } from './shared/http.js'

const router = useRouter()
const route = useRoute()
const loggingOut = ref(false)
async function logout() {
  loggingOut.value = true
  try { await request('/auth/logout', { method: 'POST', body: {} }) } catch {
    // 服务不可达时仍清除当前浏览器内存会话。
  } finally {
    clearSession()
    // 保持成员 C 的既有行为：退出登录后回到演示工作台。
    await router.replace('/demo')
    loggingOut.value = false
  }
}
watch(() => session.token, token => {
  if (!token && !loggingOut.value && route.meta.requiresAuth) router.replace({ path: '/demo', query: { next: route.fullPath } })
})
</script>

<template>
  <header class="site-header">
    <div class="header-inner">
      <RouterLink class="brand" to="/"><span class="brand-mark">归</span><span>校园失物认领<small>让物品回到主人身边</small></span></RouterLink>
      <nav aria-label="主导航">
        <RouterLink to="/demo">演示工作台</RouterLink>
        <template v-if="session.user">
          <RouterLink to="/me/claims?role=applicant">我的认领</RouterLink>
          <RouterLink to="/me/claims?role=publisher">收到的申请</RouterLink>
          <RouterLink to="/me/profile">个人中心</RouterLink>
        </template>
        <template v-else>
          <RouterLink to="/login">登录</RouterLink>
          <RouterLink to="/register">注册</RouterLink>
        </template>
      </nav>
      <div v-if="session.user" class="account">
        <span>{{ session.user.nickname }}<small>{{ session.user.is_campus_verified ? '演示认证' : '未认证' }}</small></span>
        <button class="secondary small" :disabled="loggingOut" @click="logout">退出登录</button>
      </div>
    </div>
  </header>
  <main class="container"><RouterView /></main>
  <footer class="site-footer">课程演示 · 成员 A：注册登录 / 校园身份绑定 / 个人资料 · 成员 C：认领、沟通与规则匹配 · 请勿填写真实证件信息</footer>
</template>

<style scoped>
@media (max-width: 850px) {
  nav { flex-wrap: wrap; row-gap: 2px; }
  .account { max-width: 100%; overflow-wrap: anywhere; }
}
</style>
