import type { EChartsOption } from 'echarts'
import type { ChartResponse, LineOverlay } from '../api/types'

export interface LayerVisibility { bi: boolean; segments: boolean; zones: boolean; buySellPoints: boolean; macd: boolean }
export const allLayersVisible: LayerVisibility = { bi: true, segments: true, zones: true, buySellPoints: true, macd: true }

export function buildChartOption(response: ChartResponse, visible: LayerVisibility): EChartsOption {
  const times = response.candles.map(c => c.time)
  const lines = (id: string, items: LineOverlay[], color: string) => ({
    id, name: id === 'bi' ? '笔' : '线段', type: 'scatter', data: [], xAxisIndex: 0, yAxisIndex: 0, tooltip: { show: false },
    markLine: { silent: true, symbol: ['none', 'none'], label: { show: false }, lineStyle: { color, width: id === 'bi' ? 1.5 : 2.5, opacity: .9 },
      data: items.map(item => [{ coord: [item.start_time, item.start_price] }, { coord: [item.end_time, item.end_price] }]) }
  })
  const series: any[] = [{ id: 'candles', name: 'K 线', type: 'candlestick', xAxisIndex: 0, yAxisIndex: 0,
    data: response.candles.map(c => [c.open, c.close, c.low, c.high]), tooltip: { show: false },
    itemStyle: { color: '#d95d55', color0: '#2ba880', borderColor: '#d95d55', borderColor0: '#2ba880' } }]
  if (visible.bi) series.push(lines('bi', response.overlays.bi, '#db9e4d'))
  if (visible.segments) series.push(lines('segments', response.overlays.segments, '#3e69aa'))
  if (visible.zones) series.push({ id: 'zones', name: '中枢', type: 'scatter', data: [], xAxisIndex: 0, yAxisIndex: 0, tooltip: { show: false },
    markArea: { silent: true, itemStyle: { color: 'rgba(70, 133, 174, .12)', borderColor: '#78a8c4', borderWidth: 1 },
      data: response.overlays.zones.map(z => [{ coord: [z.start_time, z.lower] }, { coord: [z.end_time, z.upper] }]) } })
  if (visible.buySellPoints) series.push({ id: 'buySellPoints', name: '买卖点', type: 'scatter', xAxisIndex: 0, yAxisIndex: 0, symbolSize: 13,
    label: { show: true, fontSize: 11, fontWeight: 'bold' },
    tooltip: { trigger: 'item', formatter: (params: { data: { name: string; value: [string, number] } }) =>
      `${params.data.name}<br/>价格：${params.data.value[1]}` },
    data: response.overlays.buy_sell_points.map(p => {
      const label = `${p.side === 'buy' ? 'b' : 's'}${p.type}`
      return { value: [p.time, p.price], name: label,
        symbol: p.side === 'buy' ? 'triangle' : 'pin', itemStyle: { color: p.side === 'buy' ? '#d95d55' : '#2ba880' },
        label: { show: true, formatter: label, position: p.side === 'buy' ? 'bottom' : 'top',
          color: p.side === 'buy' ? '#b7443e' : '#227d60' } }
    }) })
  if (visible.macd) {
    series.push({ id: 'macdHistogram', name: 'MACD', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, tooltip: { show: false },
      data: response.indicators.macd.map(m => ({ value: m.histogram, itemStyle: { color: m.histogram >= 0 ? '#d95d55' : '#2ba880' } })) })
    series.push({ id: 'dif', name: 'DIF', type: 'line', showSymbol: false, xAxisIndex: 1, yAxisIndex: 1, tooltip: { show: false }, lineStyle: { color: '#ce9b55', width: 1 }, data: response.indicators.macd.map(m => m.diff) })
    series.push({ id: 'dea', name: 'DEA', type: 'line', showSymbol: false, xAxisIndex: 1, yAxisIndex: 1, tooltip: { show: false }, lineStyle: { color: '#44699c', width: 1 }, data: response.indicators.macd.map(m => m.dea) })
  }
  return { animation: false, grid: [{ left: 58, right: 24, top: 34, height: visible.macd ? '60%' : '78%' },
      { left: 58, right: 24, top: '75%', height: '16%' }],
    xAxis: [{ type: 'category', data: times, boundaryGap: true, axisLine: { lineStyle: { color: '#dce5e0' } }, axisLabel: { color: '#779087', hideOverlap: true } },
      { type: 'category', data: times, gridIndex: 1, axisLabel: { show: false }, axisLine: { show: false } }],
    yAxis: [{ type: 'value', scale: true, boundaryGap: ['10%', '10%'], splitLine: { lineStyle: { color: '#edf2ef' } }, axisLabel: { color: '#779087' } },
      { type: 'value', scale: true, gridIndex: 1, splitLine: { lineStyle: { color: '#edf2ef' } }, axisLabel: { color: '#779087' } }],
    axisPointer: { link: [{ xAxisIndex: 'all' }], label: { show: false } },
    dataZoom: [{ type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100, zoomOnMouseWheel: false, moveOnMouseWheel: true }, { type: 'slider', xAxisIndex: [0, 1], start: 0, end: 100, bottom: 4, height: 18, borderColor: '#dce8e1', fillerColor: '#d5eee4' }],
    tooltip: { trigger: 'item', show: visible.buySellPoints, backgroundColor: '#fff', borderColor: '#dce8e1' },
    series } as EChartsOption
}
