import { test, expect } from '@playwright/test'

// 成员 A 浏览器验收：注册 → 登录 → 绑定校园身份 → 修改资料 → 退出 → 重新登录验证。
// 依赖后端 e2e 环境（scripts/e2e_backend.py 注入 DEMO_BINDING_CODE=e2e-binding-0001）。
const password = 'e2e-test-only-123'
const bindingCode = 'e2e-binding-0001'
const studentNo = '20260004'

test('注册、登录、绑定校园身份、修改资料并重新登录', async ({ browser }) => {
  test.setTimeout(90000)
  const context = await browser.newContext()
  const page = await context.newPage()
  const username = `e2e_${Date.now().toString(36)}`
  const nickname = 'E2E学生甲'
  try {
    // 0. 未登录访问受保护页面被路由守卫引导到登录页并回跳；根路径与未知路径按状态跳转。
    await page.goto('/')
    await expect(page).toHaveURL(/\/login$/)
    await page.goto('/me/profile')
    await expect(page).toHaveURL(/\/login(\?.*)?$/)
    expect(new URL(page.url()).searchParams.get('next')).toBe('/me/profile')
    await page.goto('/unknown-path')
    await expect(page).toHaveURL(/\/login$/)

    // 1. 注册：成功后不自动登录，回到登录页并提示。
    await page.goto('/register')
    await page.getByLabel('账号').fill(username)
    await page.getByLabel('昵称').fill(nickname)
    await page.getByLabel('密码', { exact: true }).fill(password)
    await page.getByLabel('确认密码').fill(password)
    await page.getByRole('button', { name: '注册', exact: true }).click()
    await expect(page).toHaveURL(/\/login\?registered=1/)
    await expect(page.getByText('注册成功', { exact: false })).toBeVisible()
    await expect(page.getByLabel('账号')).toHaveValue(username)

    // 2. 登录：进入演示工作台，头部出现个人入口与未认证标记。
    await page.getByLabel('密码', { exact: true }).fill(password)
    await page.getByRole('button', { name: '登录', exact: true }).click()
    await expect(page).toHaveURL(/\/demo$/)
    await expect(page.getByRole('button', { name: '退出登录' })).toBeVisible()
    await expect(page.locator('.account')).toContainText(nickname)
    await expect(page.locator('.account')).toContainText('未认证')

    // 3. 个人中心 → 校园身份绑定（campus_main + 20260004 + 固定绑定码）。
    await page.getByRole('link', { name: '个人中心', exact: true }).click()
    await expect(page).toHaveURL(/\/me\/profile$/)
    await page.getByRole('link', { name: '校园身份绑定' }).click()
    await expect(page).toHaveURL(/\/me\/campus-binding$/)
    const campusField = page.getByLabel('校区')
    if ((await campusField.evaluate(node => node.tagName)) === 'SELECT') await campusField.selectOption('campus_main')
    else await campusField.fill('campus_main')
    await page.getByLabel('学号').fill(studentNo)
    await page.getByLabel('绑定码').fill(bindingCode)
    await page.getByRole('button', { name: '提交绑定' }).click()
    await expect(page.getByText('校园身份绑定成功', { exact: false })).toBeVisible()
    await expect(page.getByText('****0004')).toBeVisible()
    await expect(page.getByText('演示认证').first()).toBeVisible()
    await expect(page.locator('p.notice').filter({ hasText: '第一版为演示认证，不是真实学校认证' })).toBeVisible()
    await expect(page.getByLabel('学号')).toHaveCount(0)

    // 4. 修改资料：昵称与简介保存成功，头部同步新昵称与演示认证徽标。
    await page.getByRole('link', { name: '返回个人中心', exact: true }).click()
    await expect(page).toHaveURL(/\/me\/profile$/)
    await page.getByLabel('昵称').fill('E2E学生乙')
    await page.getByLabel('简介').fill('由成员 A 浏览器验收修改的简介。')
    await page.getByRole('button', { name: '保存资料' }).click()
    await expect(page.getByText('资料已保存')).toBeVisible()
    await expect(page.locator('.account')).toContainText('E2E学生乙')
    await expect(page.locator('.account')).toContainText('演示认证')

    // 5. 退出登录仍回到 /demo（成员 C 用例依赖的既有行为）。
    await page.getByRole('button', { name: '退出登录' }).click()
    await expect(page).toHaveURL(/\/demo$/)
    await expect(page.getByText('登录演示账号')).toBeVisible()
    await expect(page.getByRole('button', { name: '退出登录' })).toHaveCount(0)

    // 6. 重新登录：资料与认证状态在服务端保持。
    await page.getByRole('link', { name: '登录', exact: true }).click()
    await expect(page).toHaveURL(/\/login$/)
    await page.getByLabel('账号').fill(username)
    await page.getByLabel('密码', { exact: true }).fill(password)
    await page.getByRole('button', { name: '登录', exact: true }).click()
    await expect(page).toHaveURL(/\/demo$/)
    await expect(page.locator('.account')).toContainText('E2E学生乙')
    await expect(page.locator('.account')).toContainText('演示认证')
    await page.getByRole('link', { name: '个人中心', exact: true }).click()
    await expect(page).toHaveURL(/\/me\/profile$/)
    await expect(page.getByLabel('昵称')).toHaveValue('E2E学生乙')
    await expect(page.getByLabel('简介')).toHaveValue('由成员 A 浏览器验收修改的简介。')

    // 7. 手机宽度（390px）无横向溢出。
    await page.setViewportSize({ width: 390, height: 844 })
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
    expect(overflow).toBe(false)
  } finally {
    await context.close()
  }
})
