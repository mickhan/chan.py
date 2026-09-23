import type { InstrumentOption } from './api/types'

const STORAGE_KEY = 'chan-chart:recent-instruments:v1'
const MAX_RECENT = 10

function isInstrumentOption(value: unknown): value is InstrumentOption {
  if (!value || typeof value !== 'object') return false
  const option = value as Record<string, unknown>
  return option.market === 'cn' &&
    typeof option.instrument === 'string' && option.instrument.length > 0 &&
    typeof option.name === 'string' && typeof option.exchange === 'string' &&
    (option.kind === 'stock' || option.kind === 'index' || option.kind === 'etf' || option.kind === 'lof')
}

export function readRecentInstruments(): InstrumentOption[] {
  try {
    const parsed: unknown = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? '[]')
    return Array.isArray(parsed) ? parsed.filter(isInstrumentOption).slice(0, MAX_RECENT) : []
  } catch {
    return []
  }
}

export function rememberInstrument(option: InstrumentOption): InstrumentOption[] {
  const next = [option, ...readRecentInstruments().filter(item => item.instrument !== option.instrument)].slice(0, MAX_RECENT)
  try { window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next)) } catch { /* Private browsing may deny storage. */ }
  return next
}
