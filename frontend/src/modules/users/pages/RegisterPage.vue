<script setup>
/**
 * 注册页 /register —— TODO [D2-06]
 *
 * 验收行为：
 * 1. 账号 4～32 位字母/数字/下划线；昵称 1～30 字；密码 8～64 位；确认密码必须一致；
 * 2. 提交 api.register；成功后不自动登录，跳 /login 并带上 registered=1 与 username；
 * 3. 失败用 errorText 提示（409 提示账号已被注册）。
 */
import { ref } from 'vue'
import { errorText } from '../../../shared/http.js'
import { register } from '../api.js'

const username = ref('')
const nickname = ref('')
const password = ref('')
const confirm = ref('')
const fieldErrors = ref({})
const formError = ref('')
const busy = ref(false)

async function submit() {
  // TODO [D2-06] 实现注册提交
}
</script>

<template>
  <div class="page-heading">
    <p class="eyebrow">SIGN UP</p>
    <h1>注册</h1>
    <p class="muted">注册后登录，再完成校园身份绑定即可发布信息与申请认领。</p>
  </div>
  <form class="panel auth-panel" novalidate @submit.prevent="submit">
    <h2>创建账号</h2>
    <p v-if="formError" class="error" role="alert">{{ formError }}</p>
    <label for="register-username">账号</label>
    <input id="register-username" v-model="username" name="username" autocomplete="username" :disabled="busy">
    <p v-if="fieldErrors.username" class="field-error">{{ fieldErrors.username }}</p>
    <label for="register-nickname">昵称</label>
    <input id="register-nickname" v-model="nickname" name="nickname" :disabled="busy">
    <p v-if="fieldErrors.nickname" class="field-error">{{ fieldErrors.nickname }}</p>
    <label for="register-password">密码</label>
    <input id="register-password" v-model="password" name="password" type="password" autocomplete="new-password" :disabled="busy">
    <p v-if="fieldErrors.password" class="field-error">{{ fieldErrors.password }}</p>
    <label for="register-confirm">确认密码</label>
    <input id="register-confirm" v-model="confirm" name="confirm" type="password" autocomplete="new-password" :disabled="busy">
    <p v-if="fieldErrors.confirm" class="field-error">{{ fieldErrors.confirm }}</p>
    <button type="submit" :disabled="busy">{{ busy ? '注册中…' : '注册' }}</button>
    <p class="muted">已有账号？<RouterLink to="/login">去登录</RouterLink></p>
  </form>
</template>

<style scoped>
.auth-panel button { width: 100%; margin: 20px 0 12px; }
.field-error { color: #994529; font-size: 13px; margin: 6px 0 0; }
</style>
