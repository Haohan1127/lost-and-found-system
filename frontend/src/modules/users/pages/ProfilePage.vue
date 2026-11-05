<script setup>
/**
 * 个人资料页 /me/profile —— TODO [D2-07]
 *
 * 验收行为：
 * 1. 进入页面用 api.me() 拉最新资料（避免刷新后拿到旧昵称）；
 * 2. 昵称 1～30 字、简介 0～200 字；保存调 api.updateMe({ nickname, bio })；
 * 3. 保存成功后同步 session.user.nickname / bio，页面提示“资料已保存”，头部昵称同步；
 * 4. 只读字段（账号、认证状态）只展示，绝不提交。
 */
import { ref } from 'vue'
import { session } from '../../../shared/session.js'
import { me, updateMe } from '../api.js'

const nickname = ref(session.user?.nickname || '')
const bio = ref(session.user?.bio || '')
const message = ref('')
const formError = ref('')
const busy = ref(false)

async function load() {
  // TODO [D2-07] 拉取最新资料并回填
}

async function save() {
  // TODO [D2-07] 前端校验 + 提交 + 同步 session
}
</script>

<template>
  <div class="page-heading">
    <p class="eyebrow">MY PROFILE</p>
    <h1>个人中心</h1>
    <p class="muted">在这里维护昵称与简介，并查看校园身份认证状态。</p>
  </div>
  <p class="notice">第一版校园认证为<b>演示认证</b>，使用预置测试身份，不是真实学校认证。</p>
  <form class="panel auth-panel" novalidate @submit.prevent="save">
    <h2>本人资料</h2>
    <p v-if="formError" class="error" role="alert">{{ formError }}</p>
    <p v-if="message" class="success" role="status">{{ message }}</p>
    <p class="muted">账号：{{ session.user?.username }} · 认证状态：
      <span>{{ session.user?.is_campus_verified ? '演示认证' : '未认证' }}</span>
    </p>
    <label for="profile-nickname">昵称</label>
    <input id="profile-nickname" v-model="nickname" name="nickname" maxlength="30" :disabled="busy">
    <label for="profile-bio">简介</label>
    <textarea id="profile-bio" v-model="bio" name="bio" rows="4" maxlength="200" :disabled="busy"></textarea>
    <button type="submit" :disabled="busy">{{ busy ? '保存中…' : '保存资料' }}</button>
    <p class="muted"><RouterLink to="/me/campus-binding">校园身份绑定</RouterLink></p>
  </form>
</template>

<style scoped>
.auth-panel button { width: 100%; margin: 20px 0 12px; }
</style>
