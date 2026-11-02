import { ref, watch, onScopeDispose } from 'vue'
import { session } from '../../../shared/session.js'
import { errorText } from '../../../shared/http.js'
import { getMessages, sendMessage } from '../api.js'

export function useClaimMessages(claimId, onRefresh = () => {}) {
  const messages = ref([])
  const error = ref('')
  const loading = ref(false)
  const sending = ref(false)
  let timer, controller, cursor = null, generation = 0, flight = null

  function stop() {
    generation += 1
    clearTimeout(timer)
    controller?.abort()
    flight = null
  }
  function refresh() {
    if (flight) return flight
    if (!claimId.value || !session.token) return Promise.resolve()
    const run = generation
    const activeId = claimId.value
    controller = new AbortController()
    const signal = controller.signal
    loading.value = true
    flight = (async () => {
      try {
        let more = true
        while (more && run === generation) {
          const batch = await getMessages(activeId, { after_id: cursor, limit: 100 }, signal)
          if (run !== generation) return
          const map = new Map(messages.value.map(message => [message.id, message]))
          batch.items.forEach(message => map.set(message.id, message))
          messages.value = [...map.values()].sort((a, b) => BigInt(a.id) < BigInt(b.id) ? -1 : BigInt(a.id) > BigInt(b.id) ? 1 : 0)
          cursor = batch.next_after_id
          more = batch.has_more
        }
        if (run === generation) {
          error.value = ''
          await onRefresh()
        }
      } catch (err) {
        if (run === generation && err.name !== 'AbortError') error.value = errorText(err)
      } finally {
        if (run === generation) { loading.value = false; flight = null }
      }
    })()
    return flight
  }
  async function poll(run) {
    await refresh()
    if (run === generation && session.token) timer = setTimeout(() => poll(run), 5000)
  }
  watch([claimId, () => session.token], () => {
    stop()
    cursor = null
    messages.value = []
    error.value = ''
    loading.value = false
    if (claimId.value && session.token) poll(generation)
  }, { immediate: true })
  onScopeDispose(stop)

  async function send(content) {
    if (sending.value) return false
    sending.value = true
    const run = generation
    try {
      const message = await sendMessage(claimId.value, content)
      if (run !== generation) return false
      if (!messages.value.some(item => item.id === message.id)) messages.value.push(message)
      await refresh()
      return true
    } catch (err) {
      if (run !== generation) return false
      await refresh()
      error.value = err.status ? errorText(err) : '发送结果未确认，已刷新消息。请检查记录后再决定是否重新发送。'
      return false
    } finally { sending.value = false }
  }
  return { messages, error, loading, sending, refresh, send }
}
