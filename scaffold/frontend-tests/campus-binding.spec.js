/**
 * 校园身份绑定页验收基线（复制到 frontend/src/modules/users/tests/campus-binding.spec.js 后生效）。
 *
 * 启用：
 *   Copy-Item scaffold\frontend-tests\campus-binding.spec.js frontend\src\modules\users\tests\campus-binding.spec.js
 *   cd frontend; npm.cmd test
 *
 * 断言口径：未绑定展示表单；/meta/campuses 不可用时降级文本输入；绑定成功展示脱敏学号；绑定码错误提示。
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { clearSession, session } from '../../../shared/session.js'
import { ApiError } from '../../../shared/http.js'
import { bindCampus, campuses, getBinding } from '../api.js'
import CampusBindingPage from '../pages/CampusBindingPage.vue'

vi.mock('../api.js', () => ({ getBinding: vi.fn(), bindCampus: vi.fn(), campuses: vi.fn() }))

const bound = {
  campus_id: 'campus_main', student_no_masked: '****0004', verification_mode: 'demo', verified_at: '2026-11-03T02:00:00Z',
}

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/me/campus-binding', component: CampusBindingPage },
      { path: '/me/profile', component: { template: '<div />' } },
    ],
  })
}

async function mountPage() {
  const router = makeRouter()
  await router.push('/me/campus-binding')
  await router.isReady()
  const wrapper = mount(CampusBindingPage, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

beforeEach(() => {
  vi.resetAllMocks()
  clearSession()
  session.token = 'token-1'
  session.user = { id: 'u1', username: 'student1', nickname: '新同学', is_campus_verified: false }
})
afterEach(() => { clearSession() })

describe('校园身份绑定页', () => {
  it('未绑定时展示表单；校区字典不可用时降级为文本输入', async () => {
    getBinding.mockResolvedValue(null)
    campuses.mockRejectedValue(new ApiError('资源不存在', 404, 'NOT_FOUND'))
    const { wrapper } = await mountPage()
    expect(wrapper.get('#binding-student-no').exists()).toBe(true)
    expect(wrapper.get('#binding-code').exists()).toBe(true)
    expect(wrapper.get('#binding-campus').element.tagName).toBe('INPUT')
    expect(wrapper.get('#binding-campus').element.value).toBe('campus_main')
    expect(wrapper.text()).toContain('演示认证')
  })

  it('已绑定时展示脱敏学号，不再展示学号输入框', async () => {
    getBinding.mockResolvedValue(bound)
    campuses.mockResolvedValue([{ id: 'campus_main', name: '主校区' }])
    const { wrapper } = await mountPage()
    expect(wrapper.text()).toContain('****0004')
    expect(wrapper.text()).toContain('演示认证')
    expect(wrapper.find('#binding-student-no').exists()).toBe(false)
  })

  it('提交成功提示并切换到已绑定视图', async () => {
    getBinding.mockResolvedValueOnce(null)
    campuses.mockResolvedValue([{ id: 'campus_main', name: '主校区' }])
    bindCampus.mockResolvedValue(bound)
    const { wrapper } = await mountPage()
    await wrapper.get('#binding-student-no').setValue('20260004')
    await wrapper.get('#binding-code').setValue('demo-binding-0001')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(bindCampus).toHaveBeenCalledWith({ campus_id: 'campus_main', student_no: '20260004', binding_code: 'demo-binding-0001' })
    expect(wrapper.text()).toContain('校园身份绑定成功')
    expect(wrapper.text()).toContain('****0004')
  })

  it('绑定码错误时提示字段错误', async () => {
    getBinding.mockResolvedValue(null)
    campuses.mockResolvedValue([{ id: 'campus_main', name: '主校区' }])
    bindCampus.mockRejectedValue(new ApiError(
      '请检查填写内容', 400, 'VALIDATION_ERROR', { binding_code: ['绑定码无效或已被使用'] }))
    const { wrapper } = await mountPage()
    await wrapper.get('#binding-student-no').setValue('20260004')
    await wrapper.get('#binding-code').setValue('wrong-code')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('绑定码无效或已被使用')
    expect(wrapper.text()).toContain('提交绑定')
  })
})
