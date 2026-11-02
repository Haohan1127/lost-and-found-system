import { session, clearSession } from './session.js'

export class ApiError extends Error {
  constructor(message, status = 0, code = 'NETWORK_ERROR', errors = {}) {
    super(message)
    Object.assign(this, { status, code, errors })
  }
}

export async function request(path, { method = 'GET', body, query, signal } = {}) {
  const base = import.meta.env.VITE_API_BASE || '/api/v1'
  const params = new URLSearchParams(Object.entries(query || {}).filter(([, value]) => value !== undefined && value !== null && value !== ''))
  const url = `${base}${path}${params.size ? `?${params}` : ''}`
  const headers = { Accept: 'application/json' }
  const token = session.token
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  let response
  try {
    response = await fetch(url, { method, headers, signal, body: body === undefined ? undefined : JSON.stringify(body) })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new ApiError('无法连接服务，请检查后端是否启动')
  }
  let result
  try { result = await response.json() } catch {
    throw new ApiError('服务返回了无法解析的响应', response.status)
  }
  if (!response.ok || result.code !== 'OK') {
    // 旧请求的 401 不清除后来登录的新会话。
    if (response.status === 401 && session.token === token) clearSession()
    throw new ApiError(result.message || '请求失败', response.status, result.code, result.errors || {})
  }
  return result.data
}

export function errorText(error) {
  const fields = Object.entries(error.errors || {}).map(([key, values]) => `${key}：${Array.isArray(values) ? values.join('；') : values}`)
  return fields.length ? fields.join('；') : error.message || '请求失败'
}
