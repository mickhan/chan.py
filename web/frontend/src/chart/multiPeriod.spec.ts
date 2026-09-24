import { describe, expect, it } from 'vitest'
import { buildChartRequests } from './multiPeriod'
import type { AnalysisRequest, PeriodCapability } from '../api/types'

const request: AnalysisRequest = { market: 'cn', instrument: 'sh.600000', period: '1d', begin_time: '2026-09-01', end_time: '2026-09-08', adjustment: 'none' }
const capabilities: PeriodCapability[] = ['5m', '30m', '1d', '1w'].map(period => ({ market: 'cn', source: 'fixture', kind: 'stock', period, adjustments: ['none'], first_available: null, last_available: null, max_bars: 5000, instrument: null }))

describe('three chart requests', () => {
  it('keeps the daily range and scales adjacent ranges around the same end date', () => {
    const charts = buildChartRequests(request, capabilities, 'stock')
    expect(charts.map(chart => chart.period)).toEqual(['30m', '1d', '1w'])
    expect(charts.map(chart => chart.request?.begin_time)).toEqual(['2026-09-08', '2026-09-01', '2026-07-31'])
    expect(charts.map(chart => chart.request?.end_time)).toEqual(['2026-09-08', '2026-09-08', '2026-09-08'])
    expect(charts[1].request).toEqual(request)
  })

  it('uses 5m and daily charts around 30m, including a leap-day boundary', () => {
    const charts = buildChartRequests({ ...request, period: '30m', begin_time: '2024-02-25', end_time: '2024-03-01' }, capabilities, 'stock')
    expect(charts.map(chart => chart.period)).toEqual(['5m', '30m', '1d'])
    expect(charts.map(chart => chart.request?.begin_time)).toEqual(['2024-03-01', '2024-02-25', '2024-01-14'])
  })

  it('clips companion requests to availability and rejects a non-overlapping range', () => {
    const bounded = capabilities.map(item => ({ ...item, first_available: '2026-09-03', last_available: '2026-09-07' }))
    const charts = buildChartRequests(request, bounded, 'stock')
    expect(charts[0].request).toBeNull()
    expect(charts[1].request).toEqual(request)
    expect(charts[2].request).toMatchObject({ begin_time: '2026-09-03', end_time: '2026-09-07' })
  })

  it('leaves unsupported periods unavailable without changing adjustment or using another instrument', () => {
    const limited = capabilities.map(item => item.period === '5m' ? { ...item, instrument: 'sh.600001' } : item.period === '1d' ? { ...item, adjustments: ['qfq'] } : item)
    const charts = buildChartRequests({ ...request, period: '30m' }, limited, 'stock')
    expect(charts.map(chart => !!chart.request)).toEqual([false, true, false])
  })
})
