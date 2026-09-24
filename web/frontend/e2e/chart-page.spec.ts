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
    : route.fulfill({ json: { ...fixture,
      candles: fixture.candles.map((c: any, i: number) => ({ ...c, is_closed: i === 0 })),
      meta: { ...fixture.meta, data_status: 'live', fetched_at: '2026-09-01T10:05:00+08:00', provisional_count: 1, warnings: [] },
    } }))
  await page.goto('/')
  await page.getByPlaceholder(/输入代码或名称/).fill('000001')
  await page.getByRole('button', { name: /上证指数.*sh.000001/ }).click()
  await expect(page.locator('#period')).toHaveValue('30m')
  await page.locator('[name="begin_time"]').fill('2026-09-01')
  await page.locator('[name="end_time"]').fill('2026-09-02')
  await page.getByRole('button', { name: '分析图表' }).click()
  await expect(page.getByRole('img', { name: '缠论 K 线图' })).toBeVisible()
  await expect(page.locator('canvas').first()).toBeVisible()
  await expect(page.getByText('盘中行情', { exact: true })).toBeVisible()
  await expect(page.getByText('1 根未收盘 · 结构与买卖点可能变化')).toBeVisible()
  await expect(page.getByText('最近取数：2026-09-01 10:05:00')).toBeVisible()
  await page.reload()
  await expect(page.getByRole('button', { name: /上证指数.*sh.000001/ })).toBeVisible()
  await page.getByRole('button', { name: /上证指数.*sh.000001/ }).click()
  await expect(page.locator('#period')).toHaveValue('30m')
  await page.locator('[name="begin_time"]').fill('2026-09-01')
  await page.locator('[name="end_time"]').fill('2026-09-02')
  await page.getByRole('button', { name: '分析图表' }).click()
  await expect(page.getByRole('img', { name: '缠论 K 线图' })).toBeVisible()
  await expect(page.getByRole('button', { name: '缩小时间范围' })).toBeVisible()
  await page.getByRole('button', { name: '放大时间范围' }).click()
  await expect(page.getByText('2 根 K 线')).toBeVisible()
  await page.getByRole('button', { name: '笔', exact: true }).click()
  await expect(page.getByRole('button', { name: '笔', exact: true })).toHaveAttribute('aria-pressed', 'false')
  empty = true
  await page.getByRole('button', { name: '分析图表' }).click()
  await expect(page.getByText('所选区间没有 K 线数据')).toBeVisible()
  await expect(page.locator('[name="begin_time"]')).toHaveValue('2026-09-01')
})

test('renders all three periods, adapts ranges, and isolates a failed companion', async ({ page }) => {
  const requests: any[] = []
  let failWeekly = false
  await page.route('**/api/v1/capabilities**', route => route.fulfill({ json: {
    ...capabilities, periods: ['5m', '30m', '1d', '1w'].map(period => ({ ...capabilities.periods[0], period, first_available: null, last_available: null })),
  } }))
  await page.route('**/api/v1/instruments**', route => route.fulfill({ json: [{ market: 'cn', instrument: 'sh.000001', name: '上证指数', exchange: 'sh', kind: 'index' }] }))
  await page.route('**/api/v1/analysis', route => {
    const request = route.request().postDataJSON()
    requests.push(request)
    if (failWeekly && request.period === '1w') return route.fulfill({ status: 503, json: { code: 'SOURCE_TIMEOUT', message: '周线行情暂时不可用' } })
    return route.fulfill({ json: { ...fixture, request, meta: { ...fixture.meta, period: request.period } } })
  })
  await page.goto('/')
  await page.getByPlaceholder(/输入代码或名称/).fill('000001')
  await page.getByRole('button', { name: /上证指数.*sh.000001/ }).click()
  await expect(page.locator('#period option')).toHaveText(['30m', '1d'])
  await expect(page.locator('#period')).toHaveValue('30m')
  await page.locator('[name="begin_time"]').fill('2026-09-01')
  await page.locator('[name="end_time"]').fill('2026-09-08')
  await page.getByRole('button', { name: '分析图表' }).click()
  await expect(page.locator('.period-panel canvas')).toHaveCount(3)
  await expect(page.locator('.period-panel h4')).toHaveText(['5m · 低一级别', '30m · 所选周期', '1d · 高一级别'])
  const canvas = page.locator('.period-panel canvas').first()
  await canvas.scrollIntoViewIfNeeded()
  await canvas.hover({ position: { x: 200, y: 150 } })
  const beforeScroll = await page.evaluate(() => window.scrollY)
  await page.mouse.wheel(0, 300)
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(beforeScroll + 100)
  for (const panel of await page.locator('.period-panel').all()) {
    await expect(panel.locator('canvas')).toBeVisible()
    await panel.getByRole('button', { name: '放大时间范围' }).click()
  }
  await page.getByRole('button', { name: '笔', exact: true }).click()
  await expect(page.getByRole('button', { name: '笔', exact: true })).toHaveAttribute('aria-pressed', 'false')
  await page.locator('#period').selectOption('1d')
  await page.getByRole('button', { name: '分析图表' }).click()
  await expect(page.locator('.period-panel h4')).toHaveText(['30m · 低一级别', '1d · 所选周期', '1w · 高一级别'])
  await expect(page.locator('.period-panel canvas')).toHaveCount(3)
  expect(requests.slice(3).map(request => request.begin_time)).toEqual(['2026-09-08', '2026-09-01', '2026-07-31'])
  const originalCanvas = await page.locator('.period-panel canvas').first().elementHandle()
  failWeekly = true
  await page.getByRole('button', { name: '刷新', exact: true }).click()
  await expect(page.getByText('刷新失败，保留上次图表：周线行情暂时不可用')).toBeVisible()
  await expect(page.locator('.period-panel canvas')).toHaveCount(3)
  expect(await originalCanvas!.evaluate(node => node.isConnected)).toBe(true)
  await page.getByRole('button', { name: '分析图表' }).click()
  await expect(page.getByText('周线行情暂时不可用')).toBeVisible()
  await expect(page.locator('.period-panel canvas')).toHaveCount(2)
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.locator('.period-panel').first().locator('canvas')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})

test('recovers an ETF companion chart when fetched history starts later than advertised', async ({ page }) => {
  const requests: any[] = []
  await page.route('**/api/v1/capabilities**', route => route.fulfill({ json: {
    market: 'cn', sources: ['fixture'], periods: ['5m', '30m', '1d', '1w'].map(period => ({ ...capabilities.periods[0], kind: 'etf', instrument: 'sh.563360', period, first_available: '2024-10-15', last_available: null })),
  } }))
  await page.route('**/api/v1/instruments**', route => route.fulfill({ json: [{ market: 'cn', instrument: 'sh.563360', name: '测试ETF', exchange: 'sh', kind: 'etf' }] }))
  await page.route('**/api/v1/analysis', route => {
    const request = route.request().postDataJSON()
    requests.push(request)
    if (request.period === '1d' && request.begin_time < '2026-01-05') return route.fulfill({ status: 400, json: { code: 'DATE_RANGE_UNAVAILABLE', message: '请求开始日期早于数据源可提供的历史范围', first_available: '2026-01-05' } })
    return route.fulfill({ json: { ...fixture, request, meta: { ...fixture.meta, instrument: request.instrument, period: request.period } } })
  })
  await page.goto('/')
  await page.getByPlaceholder(/输入代码或名称/).fill('563360')
  await page.getByRole('button', { name: /测试ETF.*sh.563360/ }).click()
  await page.locator('[name="begin_time"]').fill('2026-06-26')
  await page.locator('[name="end_time"]').fill('2026-09-24')
  await page.getByRole('button', { name: '分析图表' }).click()
  const daily = page.getByRole('region', { name: '1d 图表' })
  await expect(daily.locator('canvas')).toBeVisible()
  await expect(daily).toContainText('分析范围：2026-01-05 至 2026-09-24')
  await expect(daily).toContainText('已按可用历史缩短范围')
  await expect(page.locator('.period-panel canvas')).toHaveCount(3)
  await expect(page.locator('[name="begin_time"]')).toHaveValue('2026-06-26')
  expect(requests.filter(request => request.period === '1d').map(request => request.begin_time)).toEqual(['2024-10-15', '2026-01-05'])
})
