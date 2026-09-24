import { afterEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import App from './App.vue'
import fixture from '../e2e/fixtures/chart-response.json'

// Canvas rendering is covered by Playwright; keep network, form, and panel handling real here.
const instrument = { market: 'cn', instrument: 'sh.600000', name: '浦发银行', exchange: 'sh', kind: 'stock' }
afterEach(() => { vi.unstubAllGlobals(); localStorage.clear() })

it('shows three independently loaded panels and keeps successful charts after a companion fails', async () => {
  const requests: any[] = []
  let failDaily = false
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (url.includes('capabilities')) return { ok: true, json: async () => ({ market: 'cn', sources: ['fixture'], periods: ['5m', '30m', '1d', '1w'].map(period => ({ ...instrument, source: 'fixture', period, adjustments: ['none'], first_available: null, last_available: null, max_bars: 5000 })) }) }
    if (url.includes('instruments')) return { ok: true, json: async () => [instrument] }
    const request = JSON.parse(init!.body as string)
    requests.push(request)
    if (request.period === '5m' || (failDaily && request.period === '1d')) return { ok: false, json: async () => ({ code: 'SOURCE_TIMEOUT', message: '行情源超时' }) }
    return { ok: true, json: async () => ({ ...fixture, request, meta: { ...fixture.meta, period: request.period } }) }
  }))
  const wrapper = mount(App, { global: { stubs: { ChartView: true } } })
  await flushPromises()
  await wrapper.get('#instrument-search').setValue('600000')
  await flushPromises()
  await wrapper.get('.suggestions button').trigger('click')
  await flushPromises()
  await wrapper.get('[name="begin_time"]').setValue('2026-09-01')
  await wrapper.get('[name="end_time"]').setValue('2026-09-08')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(wrapper.findAll('.period-panel')).toHaveLength(3)
  expect(wrapper.findAll('.period-panel').map(panel => panel.get('h4').text())).toEqual(['5m · 低一级别', '30m · 所选周期', '1d · 高一级别'])
  expect(wrapper.findAllComponents({ name: 'ChartView' })).toHaveLength(2)
  expect(wrapper.get('.period-panel').text()).toContain('行情源超时')
  expect(requests.map(request => request.period)).toEqual(['5m', '30m', '1d'])
  failDaily = true
  await wrapper.get('#period').setValue('1d')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(wrapper.findAll('.period-panel').map(panel => panel.get('h4').text())).toEqual(['30m · 低一级别', '1d · 所选周期', '1w · 高一级别'])
  expect(wrapper.findAllComponents({ name: 'ChartView' })).toHaveLength(2)
  expect(requests.slice(3).map(request => request.begin_time)).toEqual(['2026-09-08', '2026-09-01', '2026-07-31'])
  wrapper.unmount()
})

it('clips a companion to the returned history boundary, but never silently clips the selected period', async () => {
  const requests: any[] = []
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (url.includes('capabilities')) return { ok: true, json: async () => ({ market: 'cn', sources: ['fixture'], periods: ['5m', '30m', '1d', '1w'].map(period => ({ ...instrument, source: 'fixture', period, adjustments: ['none'], first_available: null, last_available: null, max_bars: 5000 })) }) }
    if (url.includes('instruments')) return { ok: true, json: async () => [instrument] }
    const request = JSON.parse(init!.body as string)
    requests.push(request)
    if (request.period === '1d' && request.begin_time < '2026-01-05') return { ok: false, json: async () => ({ code: 'DATE_RANGE_UNAVAILABLE', message: '请求开始日期早于数据源可提供的历史范围', first_available: '2026-01-05' }) }
    return { ok: true, json: async () => ({ ...fixture, request, meta: { ...fixture.meta, period: request.period } }) }
  }))
  const wrapper = mount(App, { global: { stubs: { ChartView: true } } })
  await flushPromises()
  await wrapper.get('#instrument-search').setValue('600000')
  await flushPromises()
  await wrapper.get('.suggestions button').trigger('click')
  await flushPromises()
  await wrapper.get('[name="begin_time"]').setValue('2026-06-26')
  await wrapper.get('[name="end_time"]').setValue('2026-09-24')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  const daily = wrapper.findAll('.period-panel')[2]
  expect(daily.findComponent({ name: 'ChartView' }).exists()).toBe(true)
  expect(daily.get('.period-range').text()).toContain('2026-01-05 至 2026-09-24')
  expect(daily.text()).toContain('已按可用历史缩短范围')
  // 91 calendar days at 30m expand to 728 calendar days at 1d.
  expect(requests.filter(request => request.period === '1d').map(request => request.begin_time)).toEqual(['2024-09-27', '2026-01-05'])
  expect((wrapper.get('[name="begin_time"]').element as HTMLInputElement).value).toBe('2026-06-26')
  await wrapper.get('#period').setValue('1d')
  await wrapper.get('[name="begin_time"]').setValue('2024-10-15')
  requests.length = 0
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(wrapper.findAll('.period-panel')[1].text()).toContain('请求开始日期早于数据源可提供的历史范围')
  expect(requests.filter(request => request.period === '1d')).toHaveLength(1)
  wrapper.unmount()
})
