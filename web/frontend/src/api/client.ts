import type { AnalysisRequest, CapabilityResponse, ChartResponse, InstrumentOption } from './types'

export class ApiError extends Error {
  constructor(public code: string, message: string, public supportedOptions?: string[]) { super(message) }
}

async function read<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response
  try { response = await fetch(url, init) }
  catch { throw new ApiError('NETWORK_ERROR', '无法连接本机分析服务') }
  let body: any
  try { body = await response.json() }
  catch { throw new ApiError('SOURCE_ERROR', '服务返回了无法读取的数据') }
  if (!response.ok) throw new ApiError(body.code ?? 'SOURCE_ERROR', body.message ?? '请求失败', body.supported_options)
  return body as T
}

export function fetchCapabilities(market: string, instrument?: string): Promise<CapabilityResponse> {
  const query = new URLSearchParams({ market })
  if (instrument) query.set('instrument', instrument)
  return read(`/api/v1/capabilities?${query}`)
}
export function searchInstruments(market: string, query: string): Promise<InstrumentOption[]> {
  return read(`/api/v1/instruments?${new URLSearchParams({ market, q: query, limit: '20' })}`)
}
export function analyzeChart(request: AnalysisRequest): Promise<ChartResponse> {
  return read('/api/v1/analysis', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request) })
}
