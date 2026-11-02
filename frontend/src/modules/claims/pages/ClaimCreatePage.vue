<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { session } from '../../../shared/session.js'
import { errorText } from '../../../shared/http.js'
import { datetime } from '../../../shared/utils/datetime.js'
import { getPost, createClaim } from '../api.js'
import ClaimForm from '../components/ClaimForm.vue'
import { postLabels } from '../constants.js'

const route = useRoute(), router = useRouter()
const post = ref(null), loading = ref(false), busy = ref(false), error = ref(''), uncertain = ref(false)
let generation = 0
watch(() => route.query.post_id, async postId => {
  const run = ++generation
  post.value = null
  error.value = ''
  uncertain.value = false
  if (!postId || typeof postId !== 'string') { error.value = '请从招领信息选择要认领的物品'; return }
  loading.value = true
  try { const result = await getPost(postId); if (run === generation) post.value = result } catch (err) {
    if (run === generation) error.value = errorText(err)
  } finally { if (run === generation) loading.value = false }
}, { immediate: true })
const blocked = computed(() => {
  if (!post.value) return ''
  if (post.value.post_type !== 'found') return '认领申请只针对招领信息。请先从匹配结果找到对应的招领物品。'
  if (post.value.publisher.id === session.user?.id) return '你不能认领自己发布的物品。'
  if (!session.user?.is_campus_verified) return '发起认领前请完成校园身份绑定。当前演示账号未认证，请切换至已演示认证的账号。'
  if (post.value.status !== 'open') return '该物品当前不接受新的认领申请。'
  return ''
})
async function submit(verification_text) {
  if (busy.value || blocked.value || uncertain.value) return
  busy.value = true
  error.value = ''
  try {
    const claim = await createClaim({ post_id: post.value.id, verification_text })
    await router.push(`/claims/${claim.id}`)
  } catch (err) {
    error.value = errorText(err)
    uncertain.value = err.status === 0
  } finally { busy.value = false }
}
</script>

<template>
  <RouterLink class="back-link" to="/demo">← 返回工作台</RouterLink>
  <div class="page-heading"><p class="eyebrow">CLAIM APPLICATION</p><h1>申请认领</h1><p class="muted">向拾获者提供物品细节，核实后再安排交接。</p></div>
  <p v-if="loading" class="panel">正在读取物品…</p>
  <p v-if="error" class="error" role="alert">{{ error }}</p>
  <template v-if="post">
    <article class="panel source-card"><span class="badge">{{ postLabels[post.status] }}</span><h2>{{ post.title }}</h2><p>{{ post.description }}</p><p class="muted">{{ post.location.name }} · {{ datetime(post.occurred_at) }} · {{ post.publisher.nickname }}</p><p v-if="post.handover_note">交接说明：{{ post.handover_note }}</p></article>
    <p v-if="blocked" class="notice">{{ blocked }}</p>
    <p v-else-if="uncertain" class="notice">提交结果未确认，请先在 <RouterLink to="/me/claims?role=applicant">我的认领</RouterLink> 中检查是否已生成申请。</p>
    <section v-else class="panel"><ClaimForm :busy="busy" @submit="submit" /></section>
  </template>
</template>
