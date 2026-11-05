/**
 * 成员 A 浏览器验收（复制到 frontend/tests/e2e/users.spec.js 后生效）。
 *
 * 启用：
 *   Copy-Item scaffold\e2e\users.spec.js frontend\tests\e2e\users.spec.js
 *   cd frontend; npm.cmd run test:e2e
 *
 * 前置条件（D3-02 完成后再跑）：
 *   1) scripts/e2e_backend.py 注入 DJANGO_RATE_LIMIT=0 与 DEMO_BINDING_CODE=e2e-binding-0001；
 *   2) seed_demo_users（D2-04）已实现，能创建学号 20260004 的一次性身份；
 *   3) 后端 8001 / 前端 5174 由 playwright.config.js 自动拉起。
 */
import { test, expect } from '@playwright/test'

const password = 'e2e-test-only-123'
const bindingCode = 'e2e-binding-0001'
const studentNo = '20260004'

test('注册 → 登录 → 绑定校园身份 → 修改资料 → 重新登录后资料仍在', async ({ browser }) => {
  test.setTimeout(90000)
  const context = await browser.newContext()
  const page = await context.newPage()
  const username = `e2e_${Date.now().toString(36)}`
  try {
    // 0. 未登录访问受保护页面 → 登录页并带 next
    await page.goto('/me/profile')
    await expect(page).toHaveURL(/\/login(\?.*)?$/)
    expect(new URL(page.url()).searchParams.get('next')).toBe('/me/profile')

    // 1. 注册：成功回登录页并带入账号
    await page.goto('/register')
    await page.getByLabel('账号').fill(username)
    await page.getByLabel('昵称').fill('E2E学生甲')
    await page.getByLabel('密码', { exact: true }).fill(password)
    await page.getByLabel('确认密码').fill(password)
    await page.getByRole('button', { name: '注册', exact: true }).click()
    await expect(page).toHaveURL(/\/login\?registered=1/)
    await expect(page.getByText('注册成功', { exact: false })).toBeVisible()

    // 2. 登录成功进入 /demo，头部显示未认证
    await page.getByLabel('密码', { exact: true }).fill(password)
    await page.getByRole('button', { name: '登录', exact: true }).click()
    await expect(page).toHaveURL(/\/demo$/)
    await expect(page.locator('.account')).toContainText('未认证')

    // 3. 绑定校园身份：成功后显示脱敏学号与演示认证
    await page.getByRole('link', { name: '个人中心', exact: true }).click()
    await page.getByRole('link', { name: '校园身份绑定' }).click()
    const campusField = page.getByLabel('校区')
    if ((await campusField.evaluate(node => node.tagName)) === 'SELECT') await campusField.selectOption('campus_main')
    else await campusField.fill('campus_main')
    await page.getByLabel('学号').fill(studentNo)
    await page.getByLabel('绑定码').fill(bindingCode)
    await page.getByRole('button', { name: '提交绑定' }).click()
    await expect(page.getByText('校园身份绑定成功', { exact: false })).toBeVisible()
    await expect(page.getByText('****0004')).toBeVisible()
    await expect(page.getByLabel('学号')).toHaveCount(0)

    // 4. 修改资料：昵称保存后头部同步
    await page.getByRole('link', { name: '返回个人中心', exact: true }).click()
    await page.getByLabel('昵称').fill('E2E学生乙')
    await page.getByLabel('简介').fill('由浏览器验收修改的简介。')
    await page.getByRole('button', { name: '保存资料' }).click()
    await expect(page.getByText('资料已保存')).toBeVisible()
    await expect(page.locator('.account')).toContainText('E2E学生乙')

    // 5. 重新登录后资料与认证状态仍在服务端
    await page.getByRole('button', { name: '退出登录' }).click()
    await page.getByRole('link', { name: '登录', exact: true }).click()
    await page.getByLabel('账号').fill(username)
    await page.getByLabel('密码', { exact: true }).fill(password)
    await page.getByRole('button', { name: '登录', exact: true }).click()
    await expect(page.locator('.account')).toContainText('E2E学生乙')
    await page.getByRole('link', { name: '个人中心', exact: true }).click()
    await expect(page.getByLabel('昵称')).toHaveValue('E2E学生乙')
    await expect(page.getByLabel('简介')).toHaveValue('由浏览器验收修改的简介。')
  } finally {
    await context.close()
  }
})
