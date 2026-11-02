<script setup>
import { computed, ref } from 'vue'
defineProps({ busy: Boolean })
const emit = defineEmits(['submit'])
const text = ref('')
const length = computed(() => text.value.trim().length)
</script>

<template>
  <form @submit.prevent="emit('submit', text.trim())">
    <label for="verification">私有认领证明</label>
    <p class="muted">描述未公开的细节，例如钥匙数量或挂件特征。仅你和发布者可见，提交后可在会话中补充。</p>
    <textarea id="verification" v-model="text" rows="6" maxlength="1000" required placeholder="请输入至少 10 个字的认领证明" :disabled="busy" />
    <div class="form-bottom"><span class="muted">{{ length }} / 1000 字</span><button :disabled="busy || length < 10 || length > 1000">{{ busy ? '提交中…' : '提交认领申请' }}</button></div>
  </form>
</template>
