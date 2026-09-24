export interface AnalysisRequest { market: 'cn'; instrument: string; period: string; begin_time: string; end_time: string; adjustment: string }
export interface InstrumentOption { market: string; instrument: string; name: string; exchange: string; kind: 'stock' | 'index' | 'etf' | 'lof' }
export interface PeriodCapability { market: string; source: string; kind: 'stock' | 'index' | 'etf' | 'lof'; period: string; adjustments: string[]; first_available: string | null; last_available: string | null; max_bars: number; instrument: string | null }
export interface CapabilityResponse { market: string; sources: string[]; periods: PeriodCapability[] }
export interface Candle { time: string; open: number; high: number; low: number; close: number; volume: number; is_closed?: boolean }
export interface MacdPoint { time: string; diff: number; dea: number; histogram: number }
export interface LineOverlay { start_time: string; start_price: number; end_time: string; end_price: number; direction: string; is_sure: boolean | null }
export interface ZoneOverlay { start_time: string; end_time: string; lower: number; upper: number }
export interface BuySellPoint { time: string; price: number; side: 'buy' | 'sell'; type: string; bi_is_sure: boolean }
export interface ChartResponse { schema_version: 1; request: AnalysisRequest; meta: { instrument: string; period: string; source: string; first_bar: string; last_bar: string; bar_count: number; data_status?: 'historical' | 'live' | 'delayed'; fetched_at?: string | null; provisional_count?: number; warnings?: string[] }; candles: Candle[]; indicators: { macd: MacdPoint[] }; overlays: { bi: LineOverlay[]; segments: LineOverlay[]; zones: ZoneOverlay[]; buy_sell_points: BuySellPoint[] } }
