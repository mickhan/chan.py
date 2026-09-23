import { beforeEach, describe, expect, it } from 'vitest'
import { readRecentInstruments, rememberInstrument } from './recentInstruments'
import type { InstrumentOption } from './api/types'

const a: InstrumentOption = { market: 'cn', instrument: 'sh.000001', name: '上证指数', exchange: 'sh', kind: 'index' }
const b: InstrumentOption = { market: 'cn', instrument: 'sh.600000', name: '浦发银行', exchange: 'sh', kind: 'stock' }

beforeEach(() => localStorage.clear())

describe('recent instruments', () => {
  it('persists successful choices in most-recent order without duplicates', () => {
    rememberInstrument(a)
    rememberInstrument(b)
    rememberInstrument(a)
    expect(readRecentInstruments()).toEqual([a, b])
  })

  it('keeps only ten instruments and ignores invalid stored data', () => {
    for (let i = 0; i < 12; i++) rememberInstrument({ ...a, instrument: `sh.${String(i).padStart(6, '0')}` })
    expect(readRecentInstruments()).toHaveLength(10)
    expect(readRecentInstruments()[0].instrument).toBe('sh.000011')
    localStorage.setItem('chan-chart:recent-instruments:v1', '{broken')
    expect(readRecentInstruments()).toEqual([])
  })
})

describe('fund choices', () => {
  it('restores ETF and LOF from recent instruments', () => {
    const etf: InstrumentOption = { market: 'cn', instrument: 'sh.510300', name: '沪深300ETF', exchange: 'sh', kind: 'etf' }
    const lof: InstrumentOption = { market: 'cn', instrument: 'sz.160706', name: '沪深300LOF', exchange: 'sz', kind: 'lof' }
    rememberInstrument(etf)
    rememberInstrument(lof)
    expect(readRecentInstruments()).toEqual([lof, etf])
  })
})
