import type { AnalysisRequest, InstrumentOption, PeriodCapability } from '../api/types'

export interface ChartRequest {
  period: string
  request: AnalysisRequest | null
  message: string
}

export function buildChartRequests(request: AnalysisRequest, capabilities: PeriodCapability[], kind: InstrumentOption['kind']): ChartRequest[] {
  const periods = request.period === '30m' ? ['5m', '30m', '1d'] : ['30m', '1d', '1w']
  // Relative trading durations: A shares trade four hours a day, five days a week.
  const duration: Record<string, number> = { '5m': 1, '30m': 6, '1d': 48, '1w': 240 }
  const day = 86400000
  const end = Date.parse(`${request.end_time}T00:00:00Z`)
  const days = Math.round((end - Date.parse(`${request.begin_time}T00:00:00Z`)) / day) + 1
  return periods.map(period => {
    const capability = capabilities.find(item => item.market === request.market && item.kind === kind &&
      item.period === period && (!item.instrument || item.instrument === request.instrument) &&
      item.adjustments.includes(request.adjustment))
    if (!capability) return { period, request: null, message: '该周期暂无数据（当前标的或复权方式不支持）' }
    if (period === request.period) return { period, request: { ...request }, message: '' }
    const scaledDays = Math.max(1, Math.ceil(days * duration[period] / duration[request.period]))
    let begin_time = new Date(end - (scaledDays - 1) * day).toISOString().slice(0, 10)
    let end_time = request.end_time
    if (capability.first_available && begin_time < capability.first_available) begin_time = capability.first_available
    if (capability.last_available && end_time > capability.last_available) end_time = capability.last_available
    if (begin_time > end_time) return { period, request: null, message: '该周期在所选时间范围内暂无数据' }
    return { period, request: { ...request, period, begin_time, end_time }, message: '' }
  })
}
