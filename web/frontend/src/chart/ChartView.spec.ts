import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ChartView from './ChartView.vue'
import { allLayersVisible } from './buildChartOption'
import type { ChartResponse } from '../api/types'

const chart = vi.hoisted(() => ({
  setOption: vi.fn(), getOption: vi.fn(() => ({ dataZoom: [{ start: 50, end: 100 }] })),
  dispatchAction: vi.fn(), resize: vi.fn(), dispose: vi.fn(),
}))
vi.mock('echarts', () => ({ init: vi.fn(() => chart) }))
const t = '2026-09-01T10:00:00+08:00'
const response: ChartResponse = {
  schema_version: 1, request: { market: 'cn', instrument: 'sh.000001', period: '30m', begin_time: '2026-09-01', end_time: '2026-09-02', adjustment: 'none' },
  meta: { instrument: 'sh.000001', period: '30m', source: 'fixture', first_bar: t, last_bar: t, bar_count: 1 },
  candles: [{ time: t, open: 10, high: 12, low: 9, close: 11, volume: 100 }],
  indicators: { macd: [{ time: t, diff: 0, dea: 0, histogram: 0 }] },
  overlays: { bi: [], segments: [], zones: [], buy_sell_points: [] },
}

describe('ChartView zoom controls', () => {
  it('zooms into the current visible range with the plus button', async () => {
    chart.dispatchAction.mockClear()
    const wrapper = mount(ChartView, { props: { response, visibleLayers: allLayersVisible } })
    await wrapper.get('button[aria-label="放大时间范围"]').trigger('click')
    expect(chart.dispatchAction).toHaveBeenCalledWith({ type: 'dataZoom', start: 55, end: 95 })
    wrapper.unmount()
  })
  it('zooms out and keeps the current range when layers change', async () => {
    chart.getOption.mockReturnValue({ dataZoom: [{ start: 50, end: 100 }] })
    chart.dispatchAction.mockClear()
    chart.setOption.mockClear()
    const wrapper = mount(ChartView, { props: { response, visibleLayers: allLayersVisible } })
    await wrapper.get('button[aria-label="缩小时间范围"]').trigger('click')
    expect(chart.dispatchAction).toHaveBeenCalledWith({ type: 'dataZoom', start: 37.5, end: 100 })
    chart.getOption.mockReturnValue({ dataZoom: [{ start: 55, end: 95 }] })
    await wrapper.setProps({ visibleLayers: { ...allLayersVisible, bi: false } })
    const option = chart.setOption.mock.lastCall?.[0] as any
    expect(option.dataZoom[0]).toMatchObject({ start: 55, end: 95 })
    wrapper.unmount()
  })
})

const bars = (count: number): ChartResponse => ({ ...response,
  candles: Array.from({ length: count }, (_, index) => ({ ...response.candles[0]!, time: `2026-09-${String(index + 1).padStart(2, '0')}T10:00:00+08:00` })),
})
it.each([
  { start: 50, end: 100, expectedStart: 60, expectedEnd: 100 },
  { start: 25, end: 75, expectedStart: 20, expectedEnd: 60 },
])('keeps candle positions on refresh: $start–$end', async ({ start, end, expectedStart, expectedEnd }) => {
  chart.getOption.mockReturnValue({ dataZoom: [{ start, end }] })
  const wrapper = mount(ChartView, { props: { response: bars(9), visibleLayers: allLayersVisible } })
  chart.dispose.mockClear()
  await wrapper.setProps({ response: bars(11) })
  const [option, settings] = chart.setOption.mock.lastCall as any
  expect(option.dataZoom[0]).toMatchObject({ start: expectedStart, end: expectedEnd })
  expect(option.series[0].data).toHaveLength(11)
  expect(settings).toEqual({ notMerge: false, replaceMerge: ['series'] })
  expect(chart.dispose).not.toHaveBeenCalled()
  wrapper.unmount()
})
