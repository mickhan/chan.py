import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'
const fixture = JSON.parse(readFileSync(new URL('./fixtures/chart-response.json', import.meta.url), 'utf8'))
const capabilities = { market: 'cn', sources: ['fixture'], periods: [{ market: 'cn', source: 'fixture', kind: 'index', period: '30m', adjustments: ['none'], first_available: '2026-09-01', last_available: '2026-09-02', max_bars: 5000, instrument: 'sh.000001' }] }
test('searches, analyzes, toggles layers, and preserves form on no data', async ({ page }) => {
  await page.route('**/api/v1/capabilities**', route => route.fulfill({ json: capabilities }))
  await page.route('**/api/v1/instruments**', route => route.fulfill({ json: [{ market: 'cn', instrument: 'sh.000001', name: '上证指数', exchange: 'sh', kind: 'index' }] }))
  let empty = false
  await page.route('**/api/v1/analysis', route => empty
    ? route.fulfill({ status: 404, json: { code: 'NO_DATA', message: '所选区间没有 K 线数据' } })
    : route.fulfill({ json: fixture }))
  await page.goto('/')
  await page.getByPlaceholder(/输入代码或名称/).fill('000001')
  await page.getByRole('button', { name: /上证指数.*sh.000001/ }).click()
  await expect(page.locator('#period')).toHaveValue('30m')
  await page.locator('[name="begin_time"]').fill('2026-09-01')
  await page.locator('[name="end_time"]').fill('2026-09-02')
  await page.getByRole('button', { name: '分析图表' }).click()
  await expect(page.getByRole('img', { name: '缠论 K 线图' })).toBeVisible()
  await expect(page.getByText('2 根 K 线')).toBeVisible()
  await page.getByRole('button', { name: '笔', exact: true }).click()
  await expect(page.getByRole('button', { name: '笔', exact: true })).toHaveAttribute('aria-pressed', 'false')
  empty = true
  await page.getByRole('button', { name: '分析图表' }).click()
  await expect(page.getByText('所选区间没有 K 线数据')).toBeVisible()
  await expect(page.locator('[name="begin_time"]')).toHaveValue('2026-09-01')
})
