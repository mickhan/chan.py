import { describe, expect, it } from 'vitest'
import { buildChartOption, allLayersVisible } from './buildChartOption'
import type { ChartResponse } from '../api/types'
const t0 = '2026-09-01T10:00:00+08:00', t1 = '2026-09-01T10:30:00+08:00'
const fixture: ChartResponse = { schema_version: 1, request: { market: 'cn', instrument: 'sh.000001', period: '30m', begin_time: '2026-09-01', end_time: '2026-09-02', adjustment: 'none' }, meta: { instrument: 'sh.000001', period: '30m', source: 'fixture', first_bar: t0, last_bar: t1, bar_count: 2 }, candles: [{ time: t0, open: 10, close: 12, low: 9, high: 13, volume: 100 }, { time: t1, open: 12, close: 11, low: 10, high: 14, volume: 120 }], indicators: { macd: [{ time: t0, diff: 1, dea: .5, histogram: 1 }, { time: t1, diff: .8, dea: .6, histogram: .4 }] }, overlays: { bi: [{ start_time: t0, start_price: 9, end_time: t1, end_price: 14, direction: 'up', is_sure: true }], segments: [], zones: [{ start_time: t0, end_time: t1, lower: 10, upper: 12 }], buy_sell_points: [{ time: t1, price: 14, side: 'buy', type: '1', bi_is_sure: true }] } }
describe('chart options', () => {
  it('uses candle order and response timestamps', () => {
    const option = buildChartOption(fixture, allLayersVisible) as any
    expect(option.series.find((s: any) => s.id === 'candles').data[0]).toEqual([10, 12, 9, 13])
    expect(option.xAxis[0].data[0]).toBe(t0)
    expect(option.dataZoom).toBeDefined()
    expect(option.axisPointer).toBeDefined()
  })
  it('maps overlays and toggles without changing candles', () => {
    const option = buildChartOption(fixture, allLayersVisible) as any
    expect(option.series.find((s: any) => s.id === 'bi').markLine.data[0][0].coord).toEqual([t0, 9])
    expect(option.series.find((s: any) => s.id === 'zones').markArea.data[0][1].coord).toEqual([t1, 12])
    expect(option.series.find((s: any) => s.id === 'buySellPoints').data[0].value).toEqual([t1, 14])
    expect(option.series.find((s: any) => s.id === 'macdHistogram').data).toHaveLength(2)
    const hidden = buildChartOption(fixture, { ...allLayersVisible, bi: false, macd: false }) as any
    expect(hidden.series.find((s: any) => s.id === 'bi')).toBeUndefined()
    expect(hidden.series.find((s: any) => s.id === 'candles')).toBeDefined()
  })
})
