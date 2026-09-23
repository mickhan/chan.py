<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import type { ChartResponse } from '../api/types'
import { buildChartOption, type LayerVisibility } from './buildChartOption'
const props = defineProps<{ response: ChartResponse; visibleLayers: LayerVisibility }>()
const root = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null
function resize() { chart?.resize() }
onMounted(() => { if (root.value) { chart = echarts.init(root.value); chart.setOption(buildChartOption(props.response, props.visibleLayers)); window.addEventListener('resize', resize) } })
watch(() => [props.response, props.visibleLayers], () => { chart?.setOption(buildChartOption(props.response, props.visibleLayers), true) }, { deep: true })
onBeforeUnmount(() => { window.removeEventListener('resize', resize); chart?.dispose(); chart = null })
</script>
<template><div ref="root" class="chart-view" role="img" aria-label="缠论 K 线图" /></template>
