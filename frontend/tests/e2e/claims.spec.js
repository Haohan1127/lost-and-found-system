import { test, expect } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
const password = 'e2e-test-only-123'

async function login(page, username, next = '') {
  await page.goto(`/demo${next ? `?next=${encodeURIComponent(next)}` : ''}`)
  await page.getByLabel('选择身份').selectOption(username)
  await page.getByLabel('演示密码').fill(password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page.getByRole('button', { name: '退出登录' })).toBeVisible()
}
async function apply(page, title, proof) {
  await page.getByRole('link', { name: '演示工作台' }).click()
  const card = page.locator('.post-card').filter({ has: page.getByRole('heading', { name: title, exact: true }) })
  await card.getByRole('link', { name: '申请认领', exact: true }).click()
  await page.getByLabel('私有认领证明').fill(proof)
  await page.getByRole('button', { name: '提交认领申请' }).click()
  await expect(page).toHaveURL(/\/claims\/\d+$/)
  return page.url().split('/').at(-1)
}
async function review(page, title, applicantName = '失主小周') {
  await page.getByRole('link', { name: '收到的申请', exact: true }).click()
  await page.locator('.claim-row').filter({ hasText: title }).filter({ hasText: applicantName }).first().click()
  await expect(page.locator('.badge.large')).toHaveText('待核实')
}
async function accept(page) {
  await page.getByRole('button', { name: '同意认领', exact: true }).click()
  await page.getByLabel('交接说明（选填）').fill('请在图书馆服务台核实交接。')
  await page.getByRole('button', { name: '确认同意', exact: true }).click()
  await expect(page.locator('.badge.large')).toHaveText('等待交接')
}
async function confirm(page) {
  await page.getByRole('button', { name: '确认交接', exact: true }).click()
  await page.getByRole('button', { name: '我已完成交接', exact: true }).click()
}

test('多账号认领、私有沟通、竞争关闭和双向确认', async ({ browser }) => {
  test.setTimeout(75000)
  const applicantContext = await browser.newContext()
  const publisherContext = await browser.newContext()
  const competitorContext = await browser.newContext()
  const applicant = await applicantContext.newPage()
  const publisher = await publisherContext.newPage()
  const competitor = await competitorContext.newPage()
  try {
    await login(applicant, 'applicant')
    const id = await apply(applicant, '图书馆拾到蓝色钥匙', '钥匙共有三把，挂着蓝色的小熊挂件。')
    await applicant.getByLabel('发送消息', { exact: true }).fill('私有消息：我的挂件背面刻有星星。')
    await applicant.getByRole('button', { name: '发送消息', exact: true }).click()
    await expect(applicant.locator('.message-bubble')).toHaveText('私有消息：我的挂件背面刻有星星。')

    await login(competitor, 'competitor')
    await apply(competitor, '图书馆拾到蓝色钥匙', '我也丢失了一串钥匙，申请核实物品细节。')

    await login(publisher, 'publisher')
    await review(publisher, '图书馆拾到蓝色钥匙')
    await expect(publisher.locator('.message-bubble')).toHaveText('私有消息：我的挂件背面刻有星星。')
    await publisher.getByLabel('发送消息', { exact: true }).fill('特征相符，请来图书馆服务台交接。')
    await publisher.getByRole('button', { name: '发送消息', exact: true }).click()
    await expect(applicant.locator('.message-bubble').last()).toHaveText('特征相符，请来图书馆服务台交接。', { timeout: 10000 })
    await accept(publisher)
    await expect(competitor.locator('.badge.large')).toHaveText('已关闭', { timeout: 10000 })
    await expect(competitor.getByText('发布者选择了其他申请', { exact: false })).toBeVisible()

    await login(competitor, 'competitor', `/claims/${id}`)
    await expect(competitor.getByRole('alert')).toContainText('资源不存在')
    await expect(competitor.getByText('钥匙共有三把，挂着蓝色的小熊挂件。')).toHaveCount(0)
    await expect(competitor.locator('.chat-log')).toHaveCount(0)

    await expect(applicant.getByRole('button', { name: '确认交接', exact: true })).toBeVisible({ timeout: 10000 })
    await confirm(applicant)
    await expect(applicant.locator('.badge.large')).toHaveText('等待交接')
    await expect(applicant.getByRole('button', { name: '取消申请', exact: true })).toHaveCount(0)
    await confirm(publisher)
    await expect(publisher.locator('.badge.large')).toHaveText('已完成')
    await expect(applicant.locator('.badge.large')).toHaveText('已完成', { timeout: 10000 })
    await expect(applicant.getByLabel('发送消息', { exact: true })).toHaveCount(0)
    await expect(publisher.getByText('双方均已确认，认领与招领信息已完成。')).toBeVisible()
    await publisher.screenshot({ path: path.join(root, 'docs/screenshots/member-c-handover.png'), fullPage: true })
  } finally {
    await applicantContext.close()
    await publisherContext.close()
    await competitorContext.close()
  }
})

test('交接前取消会重新开放物品且允许新申请', async ({ browser }) => {
  const applicantContext = await browser.newContext(), publisherContext = await browser.newContext()
  const applicant = await applicantContext.newPage(), publisher = await publisherContext.newPage()
  try {
    await login(applicant, 'applicant')
    const first = await apply(applicant, '图书馆拾到钥匙（取消演示）', '钥匙有两把，其中一把带有圆形的挂件。')
    await login(publisher, 'publisher')
    await review(publisher, '图书馆拾到钥匙（取消演示）')
    await accept(publisher)
    await publisher.getByRole('button', { name: '取消申请', exact: true }).click()
    await publisher.getByRole('button', { name: '确认取消', exact: true }).click()
    await expect(publisher.locator('.badge.large')).toHaveText('已取消')
    const second = await apply(applicant, '图书馆拾到钥匙（取消演示）', '补充证明：钥匙有两把和一个圆形小挂件。')
    expect(second).not.toBe(first)
  } finally { await applicantContext.close(); await publisherContext.close() }
})

test('撤回关闭申请，恢复后历史保持关闭', async ({ browser }) => {
  const applicantContext = await browser.newContext(), publisherContext = await browser.newContext()
  const applicant = await applicantContext.newPage(), publisher = await publisherContext.newPage()
  try {
    await login(applicant, 'applicant')
    await apply(applicant, '图书馆拾到钥匙（撤回演示）', '钥匙挂件是蓝色的，上面写着一个字母。')
    await login(publisher, 'publisher')
    const card = publisher.locator('.post-card').filter({ hasText: '图书馆拾到钥匙（撤回演示）' })
    await card.getByRole('button', { name: '演示撤回' }).click()
    await expect(card.locator('.badge')).toHaveText('已撤回')
    await expect(applicant.locator('.badge.large')).toHaveText('已关闭', { timeout: 10000 })
    await expect(applicant.getByText('发布者已撤回信息', { exact: false })).toBeVisible()
    await card.getByRole('button', { name: '演示恢复' }).click()
    await expect(card.locator('.badge')).toHaveText('进行中')
    await applicant.getByRole('button', { name: '刷新消息', exact: true }).click()
    await expect(applicant.locator('.badge.large')).toHaveText('已关闭')
  } finally { await applicantContext.close(); await publisherContext.close() }
})

test('匹配线索可进入认领页面，未认证账号被阻止', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } })
  const page = await context.newPage()
  try {
    await login(page, 'applicant')
    await page.locator('.post-card').filter({ hasText: '遗失蓝色钥匙' }).getByRole('link', { name: '查找匹配' }).click()
    await expect(page.locator('.match-card').first()).toBeVisible()
    await expect(page.getByText('不是失主身份概率', { exact: false })).toBeVisible()
    await expect(page.locator('.match-card').first().getByText('类别相同 +40', { exact: true })).toBeVisible()
    await page.screenshot({ path: path.join(root, 'docs/screenshots/member-c-mobile-matches.png'), fullPage: true })
    await page.locator('.match-card').first().getByRole('link', { name: '核实并申请认领' }).click()
    await expect(page.getByLabel('私有认领证明')).toBeVisible()
    await page.getByRole('button', { name: '退出登录' }).click()
    await page.getByLabel('选择身份').selectOption('unverified')
    await page.getByLabel('演示密码').fill(password)
    await page.getByRole('button', { name: '登录', exact: true }).click()
    await page.locator('.post-card').filter({ hasText: '图书馆拾到钥匙（撤回演示）' }).getByRole('link', { name: '申请认领', exact: true }).click()
    await expect(page.getByText('当前演示账号未认证', { exact: false })).toBeVisible()
    await expect(page.getByLabel('私有认领证明')).toHaveCount(0)
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
    expect(overflow).toBe(false)
  } finally { await context.close() }
})
