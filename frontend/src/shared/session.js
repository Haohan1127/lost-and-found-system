import { reactive } from 'vue'

export const session = reactive({ token: null, user: null })
export function setSession(data) {
  session.user = data.user
  session.token = data.access_token
}
export function clearSession() {
  session.token = null
  session.user = null
}
