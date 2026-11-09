<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { session, setSession } from '../shared/session.js'
import { request, errorText } from '../shared/http.js'
import { datetime } from '../shared/utils/datetime.js'
import { postLabels } from '../modules/claims/constants.js'
const route = useRoute(), router = useRouter()
const username = ref('applicant'), password = ref(''), error = ref(''), busy = ref(false), loading = ref(false), posts = ref([])
const actionBusy = ref(null)
let generation = 0
async function login() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    const result = await request('/auth/login', { method: 'POST', body: { username: username.value, password: password.value } })
    setSession(result)
    password.value = ''
    const next = route.query.next
    if (typeof next === 'string' && next.startsWith('/') && !next.startsWith('//')) await router.replace(next)
  } catch (err) { error.value = errorText(err) }
  finally { busy.value = false }
}
async function load() {
  const run = ++generation
  if (!session.token) { posts.value = []; return }
  loading.value = true
  error.value = ''
  try { const result = await request('/demo/posts', { query: { page_size: 100 } }); if (run === generation) posts.value = result.items }
  catch (err) { if (run === generation) error.value = errorText(err) }
  finally { if (run === generation) loading.value = false }
}
watch(() => session.token, load, { immediate: true })
async function changePost(post, action) {
  actionBusy.value = post.id
  error.value = ''
  try { await request(`/demo/posts/${post.id}/${action}`, { method: 'POST', body: {} }); await load() }
  catch (err) { error.value = errorText(err) }
  finally { actionBusy.value = null }
}
</script>

<template>
  <div class="page-heading"><p class="eyebrow">CAMPUS LOST & FOUND</p><h1>每一份失而复得，<br>从认真核实开始。</h1><p class="muted">提交认领证明，与拾获者沟通，双方确认后完成交接。</p></div>
  <p class="notice">当前为完整演示版：注册、登录、校园身份绑定、个人中心已接入；发布与图片上传由成员 B 接入。</p>
  <p v-if="error" class="error" role="alert">{{ error }}</p>
  <p v-if="session.user && !session.user.is_campus_verified" class="notice" style="border-color:#f0c36d;background:#fff8e1">
    当前账号未完成校园身份认证，暂时无法申请认领或发布信息。
    <RouterLink class="button small" to="/me/campus-binding?next=/demo">去完成校园身份认证</RouterLink>
  </p>
  <div v-if="!session.user" class="login-grid">
    <form class="panel login-panel" @submit.prevent="login"><h2>登录演示账号</h2><label for="demo-user">选择身份</label><select id="demo-user" v-model="username"><option value="applicant">applicant · 失主小周</option><option value="publisher">publisher · 拾获者小林</option><option value="competitor">competitor · 竞争申请者</option><option value="unverified">unverified · 未认证同学</option></select><label for="demo-password">演示密码</label><input id="demo-password" v-model="password" type="password" autocomplete="current-password" required minlength="8" maxlength="64" placeholder="初始化命令输出的密码"><button :disabled="busy">{{ busy ? '登录中…' : '登录' }}</button><p class="muted">密码由 seed_demo 输出。刷新页面后需要重新登录。</p></form>
    <section class="intro-list"><article><span>01</span><div><h2>提交可核实的细节</h2><p>公开信息之外的特征，通过私有申请告诉拾获者。</p></div></article><article><span>02</span><div><h2>在申请内沟通</h2><p>核实物品和交接安排，会话只对双方开放。</p></div></article><article><span>03</span><div><h2>双方各自确认</h2><p>实际交接后各自确认，单方确认不会完成认领。</p></div></article></section>
  </div>
  <template v-else>
    <div class="section-heading"><h2>演示物品</h2><button class="secondary" :disabled="loading" @click="load">刷新物品</button></div>
    <p v-if="loading" class="muted">正在加载物品…</p>
    <p v-if="!loading && !posts.length" class="panel empty">还没有演示数据，请先运行 seed_demo。</p>
    <div class="match-grid">
      <article v-for="post in posts" :key="post.id" class="panel post-card">
        <div class="section-heading"><span class="tag">{{ post.post_type === 'found' ? '招领' : '寻物' }}</span><span class="badge" :data-status="post.status">{{ postLabels[post.status] }}</span></div><h2>{{ post.title }}</h2><p class="muted">{{ post.location.name }} · {{ datetime(post.occurred_at) }}<br>发布者：{{ post.publisher.nickname }}{{ post.publisher.id === session.user.id ? '（我）' : '' }}</p>
        <div class="actions">
          <RouterLink v-if="post.post_type === 'found' && post.status === 'open' && post.publisher.id !== session.user.id" class="button" :to="`/claims/new?post_id=${post.id}`">申请认领</RouterLink>
          <RouterLink v-if="post.publisher.id === session.user.id && post.status === 'open'" class="button" :to="`/posts/${post.id}/matches`">查找匹配</RouterLink>
          <template v-if="post.publisher.id === session.user.id"><button v-if="post.status === 'open'" class="secondary" :disabled="actionBusy !== null" @click="changePost(post, 'withdraw')">演示撤回</button><button v-if="post.status === 'withdrawn'" class="secondary" :disabled="actionBusy !== null" @click="changePost(post, 'restore')">演示恢复</button></template>
        </div>
      </article>
    </div>
  </template>
</template>
