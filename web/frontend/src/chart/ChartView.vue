<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import type { ChartResponse } from '../api/types'
import { buildChartOption, type LayerVisibility } from './buildChartOption'

const props = defineProps<{ response: ChartResponse; visibleLayers: LayerVisibility }>()
const root = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

function resize() { chart?.resize() }
function currentRange(): { start: number; end: number } {
  const zoom = chart?.getOption().dataZoom
  const first = Array.isArray(zoom) ? zoom[0] : zoom
  return { start: Number(first?.start ?? 0), end: Number(first?.end ?? 100) }
}
function zoom(direction: 'in' | 'out') {
  if (!chart) return
  const { start, end } = currentRange()
  const width = Math.min(100, Math.max(5, (end - start) * (direction === 'in' ? 0.8 : 1.25)))
  const center = (start + end) / 2
  const nextStart = Math.min(100 - width, Math.max(0, center - width / 2))
  chart.dispatchAction({ type: 'dataZoom', start: nextStart, end: nextStart + width })
}
function render(preserveRange: boolean, previous?: ChartResponse) {
  if (!chart) return
  let range = preserveRange ? currentRange() : null
  if (range && previous && previous.candles.length > 1 && props.response.candles.length > 1) {
    const oldLast = previous.candles.length - 1
    const newLast = props.response.candles.length - 1
    const startIndex = Math.round(range.start / 100 * oldLast)
    const endIndex = Math.round(range.end / 100 * oldLast)
    if (endIndex === oldLast) {
      range = { start: Math.max(0, newLast - (endIndex - startIndex)) / newLast * 100, end: 100 }
    } else {
      const times = props.response.candles.map(candle => candle.time)
      const locate = (time: string) => {
        const index = times.findIndex(candidate => candidate >= time)
        return index < 0 ? newLast : index
      }
      range = { start: locate(previous.candles[startIndex]!.time) / newLast * 100,
        end: locate(previous.candles[endIndex]!.time) / newLast * 100 }
    }
  }
  const option = buildChartOption(props.response, props.visibleLayers)
  if (range && Array.isArray(option.dataZoom)) {
    for (const item of option.dataZoom) {
      item.start = range.start
      item.end = range.end
    }
  }
  chart.setOption(option, { notMerge: false, replaceMerge: ['series'] })
}
onMounted(() => {
  if (root.value) {
    chart = echarts.init(root.value)
    render(false)
    window.addEventListener('resize', resize)
  }
})
watch(() => props.response, (response, previous) => {
  const sameQuery = JSON.stringify(response.request) === JSON.stringify(previous.request)
  render(sameQuery, sameQuery ? previous : undefined)
})
watch(() => props.visibleLayers, () => render(true), { deep: true })
onBeforeUnmount(() => { window.removeEventListener('resize', resize); chart?.dispose(); chart = null })
</script>
<template>
  <div class="chart-shell">
    <div class="chart-zoom-controls">
      <span>滚轮上下滚动页面 · 拖动下方滑块调整范围</span>
      <div class="chart-zoom-buttons">
        <button type="button" aria-label="缩小时间范围" title="显示更多 K 线" @click="zoom('out')">−</button>
        <button type="button" aria-label="放大时间范围" title="显示更少 K 线" @click="zoom('in')">+</button>
      </div>
    </div>
    <div ref="root" class="chart-view" role="img" aria-label="缠论 K 线图" />
  </div>
</template>
