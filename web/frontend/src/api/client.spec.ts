import { describe, expect, it, vi } from 'vitest'
import { analyzeChart, ApiError, fetchCapabilities, searchInstruments } from './client'

describe('API client', () => {
  it('uses same-origin versioned endpoints', async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ market: 'cn', sources: [], periods: [] }) })
    vi.stubGlobal('fetch', fetcher)
    await fetchCapabilities('cn')
    expect(fetcher.mock.calls[0][0]).toBe('/api/v1/capabilities?market=cn')
    await searchInstruments('cn', '000001')
    expect(fetcher.mock.calls[1][0]).toContain('/api/v1/instruments?')
  })
  it('preserves structured API errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({ code: 'NO_DATA', message: '没有数据' }) }))
    await expect(analyzeChart({ market: 'cn', instrument: 'sh.000001', period: '1d', begin_time: '2026-09-01', end_time: '2026-09-02', adjustment: 'none' })).rejects.toMatchObject({ code: 'NO_DATA', message: '没有数据' })
  })
})
