<script setup>
/**
 * 登录页 /login —— TODO [D2-05]
 *
 * 验收行为（对照 scaffold/frontend-tests/login.spec.js）：
 * 1. 空值先在前端提示，不发请求；
 * 2. 调 api.login → setSession(data) → 回跳 next；next 只接受站内相对路径（'/' 开头且非 '//'），否则回 /demo；
 * 3. 失败用 errorText 统一提示，不写入会话；
 * 4. 提交期间按钮禁用并显示“登录中…”。
 * 另：/login?registered=1&username=xxx 时提示“注册成功”并把账号带入输入框。
 */
import { ref } from 'vue'
import { setSession } from '../../../shared/session.js'
import { errorText } from '../../../shared/http.js'
import { login } from '../api.js'

const username = ref('')
const password = ref('')
const fieldErrors = ref({})
const formError = ref('')
const busy = ref(false)

async function submit() {
  // TODO [D2-05] 实现登录提交
}
</script>

<template>
  <div class="page-heading">
    <p class="eyebrow">SIGN IN</p>
    <h1>登录</h1>
    <p class="muted">登录后可管理个人资料、绑定校园身份并参与失物认领。</p>
  </div>
  <form class="panel auth-panel" novalidate @submit.prevent="submit">
    <h2>账号登录</h2>
    <p v-if="formError" class="error" role="alert">{{ formError }}</p>
    <label for="login-username">账号</label>
    <input id="login-username" v-model="username" name="username" autocomplete="username" :disabled="busy">
    <p v-if="fieldErrors.username" class="field-error">{{ fieldErrors.username }}</p>
    <label for="login-password">密码</label>
    <input id="login-password" v-model="password" name="password" type="password" autocomplete="current-password" :disabled="busy">
    <p v-if="fieldErrors.password" class="field-error">{{ fieldErrors.password }}</p>
    <button type="submit" :disabled="busy">{{ busy ? '登录中…' : '登录' }}</button>
    <p class="muted">还没有账号？<RouterLink to="/register">注册新账号</RouterLink> · <RouterLink to="/demo">演示工作台</RouterLink></p>
  </form>
</template>

<style scoped>
.auth-panel button { width: 100%; margin: 20px 0 12px; }
.field-error { color: #994529; font-size: 13px; margin: 6px 0 0; }
</style>
