import { request } from '../../shared/http.js'

// 成员 A 的接口封装：页面不得自行拼路径，统一走 shared/http.js（自动带 Bearer、统一错误封装）。
export const register = payload => request('/auth/register', { method: 'POST', body: payload })
export const login = ({ username, password }) => request('/auth/login', { method: 'POST', body: { username, password } })
export const logout = () => request('/auth/logout', { method: 'POST', body: {} })
export const me = () => request('/users/me')
export const updateMe = patch => request('/users/me', { method: 'PATCH', body: patch })
export const getBinding = () => request('/users/me/campus-binding')
export const bindCampus = payload => request('/users/me/campus-binding', { method: 'POST', body: payload })
// 校区字典由成员 B 提供（/meta/campuses）；接口不可用时绑定页降级为文本输入。
export const campuses = () => request('/meta/campuses')
