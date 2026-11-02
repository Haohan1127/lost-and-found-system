import { request } from '../../shared/http.js'

// 成员 A 的用户管理接口；页面不得自行拼接路径，统一经 shared/http.js 发送。
export const register = payload => request('/auth/register', { method: 'POST', body: payload })
export const login = ({ username, password }) => request('/auth/login', { method: 'POST', body: { username, password } })
export const logout = () => request('/auth/logout', { method: 'POST', body: {} })
export const me = () => request('/users/me')
export const updateMe = patch => request('/users/me', { method: 'PATCH', body: patch })
export const getBinding = () => request('/users/me/campus-binding')
export const bindCampus = payload => request('/users/me/campus-binding', { method: 'POST', body: payload })
// 校区字典由成员 B 提供；接口不可用时页面降级为文本输入。
export const campuses = () => request('/meta/campuses')
