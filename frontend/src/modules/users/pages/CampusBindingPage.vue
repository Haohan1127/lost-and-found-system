<script setup>
/**
 * 校园身份绑定页 /me/campus-binding —— TODO [D2-08]
 *
 * 验收行为：
 * 1. 进入页面 api.getBinding()：已绑定展示 campus_id、脱敏学号（****0004）、演示认证与绑定时间；
 *    未绑定（data 为 null）展示绑定表单；
 * 2. 提交 api.bindCampus({ campus_id, student_no, binding_code }) → 成功后展示“校园身份绑定成功”并切到已绑定视图；
 * 3. 校区下拉优先用 api.campuses()（成员 B 的 /meta/campuses）；接口不可用时降级为文本输入，默认 campus_main；
 * 4. 错误提示使用 errorText（绑定码错误提示在 binding_code 字段上）。
 */
import { ref } from 'vue'
import { errorText } from '../../../shared/http.js'
import { bindCampus, campuses, getBinding } from '../api.js'

const binding = ref(null)
const loading = ref(false)
const busy = ref(false)
const campusOptions = ref([])
const campusId = ref('campus_main')
const studentNo = ref('')
const bindingCode = ref('')
const formError = ref('')
const message = ref('')

async function load() {
  // TODO [D2-08] 查询绑定状态 + 加载校区字典（失败时降级文本输入）
}

async function submit() {
  // TODO [D2-08] 提交绑定
}
</script>

<template>
  <div class="page-heading">
    <p class="eyebrow">CAMPUS IDENTITY</p>
    <h1>校园身份绑定</h1>
    <p class="muted">绑定后才能发布信息、申请认领。</p>
  </div>
  <p class="notice">第一版为<b>演示认证</b>，不是真实学校认证：只用预置校区、学号与一次性绑定码，请勿填写真实证件信息。</p>
  <p v-if="loading" class="muted">正在加载绑定状态…</p>
  <section v-else-if="binding" class="panel">
    <h2>已完成绑定</h2>
    <p>校区：{{ binding.campus_id }} · 学号：{{ binding.student_no_masked }}</p>
    <p>认证方式：演示认证 · 绑定时间：{{ binding.verified_at }}</p>
    <p class="muted"><RouterLink to="/me/profile">返回个人中心</RouterLink></p>
  </section>
  <form v-else class="panel auth-panel" novalidate @submit.prevent="submit">
    <h2>提交绑定信息</h2>
    <p v-if="formError" class="error" role="alert">{{ formError }}</p>
    <p v-if="message" class="success" role="status">{{ message }}</p>
    <label for="binding-campus">校区</label>
    <select v-if="campusOptions.length" id="binding-campus" v-model="campusId" :disabled="busy">
      <option v-for="item in campusOptions" :key="item.id" :value="item.id">{{ item.name }}</option>
    </select>
    <input v-else id="binding-campus" v-model="campusId" name="campus_id" placeholder="campus_main" :disabled="busy">
    <label for="binding-student-no">学号</label>
    <input id="binding-student-no" v-model="studentNo" name="student_no" :disabled="busy">
    <label for="binding-code">绑定码</label>
    <input id="binding-code" v-model="bindingCode" name="binding_code" :disabled="busy">
    <button type="submit" :disabled="busy">{{ busy ? '提交中…' : '提交绑定' }}</button>
    <p class="muted"><RouterLink to="/me/profile">返回个人中心</RouterLink></p>
  </form>
</template>

<style scoped>
.auth-panel button { width: 100%; margin: 20px 0 12px; }
</style>
