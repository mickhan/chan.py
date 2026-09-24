<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { analyzeChart, fetchCapabilities, searchInstruments, ApiError } from './api/client'
import type { AnalysisRequest, CapabilityResponse, ChartResponse, InstrumentOption } from './api/types'
import QueryForm from './components/QueryForm.vue'
import { readRecentInstruments, rememberInstrument } from './recentInstruments'
import ChartStatus from './components/ChartStatus.vue'
import ChartView from './chart/ChartView.vue'
import LayerToggles from './components/LayerToggles.vue'
import DataFreshness from './components/DataFreshness.vue'
import { allLayersVisible, type LayerVisibility } from './chart/buildChartOption'
import { buildChartRequests, type ChartRequest } from './chart/multiPeriod'
const capabilities = ref<CapabilityResponse | null>(null)
const selectedInstrument = ref<InstrumentOption | null>(null)
const suggestions = ref<InstrumentOption[]>([])
const recentInstruments = ref<InstrumentOption[]>([])
type ChartState = 'idle' | 'loading' | 'empty' | 'error'
interface ChartPanel extends ChartRequest { response: ChartResponse | null; state: ChartState }
const charts = ref<ChartPanel[]>([])
const analyzedName = ref('')
const analyzedPeriod = ref('')
const lastRequest = ref<AnalysisRequest | null>(null)
let lastInstrument: InstrumentOption | null = null
let analysisToken = 0
const state = ref<'idle' | 'loading' | 'empty' | 'error'>('idle')
const message = ref('')
const busy = ref(false)
const visibleLayers = ref<LayerVisibility>({ ...allLayersVisible })
let searchToken = 0
onMounted(async () => { recentInstruments.value = readRecentInstruments(); try { capabilities.value = await fetchCapabilities('cn') } catch (error) { state.value = 'error'; message.value = (error as Error).message } })
async function search(query: string) {
  const token = ++searchToken
  try { const result = await searchInstruments('cn', query); if (token === searchToken) suggestions.value = result }
  catch (error) { if (token === searchToken) { state.value = 'error'; message.value = (error as Error).message } }
}
async function pick(option: InstrumentOption) {
  selectedInstrument.value = option; suggestions.value = []
  try { capabilities.value = await fetchCapabilities('cn', option.instrument) }
  catch (error) { state.value = 'error'; message.value = (error as Error).message }
}
function clear() {
  ++analysisToken; busy.value = false; selectedInstrument.value = null; charts.value = []; lastRequest.value = null; state.value = 'idle'
  void fetchCapabilities('cn').then(value => capabilities.value = value).catch(error => { state.value = 'error'; message.value = (error as Error).message })
}
async function refresh() {
  if (lastRequest.value) await analyze(lastRequest.value, true)
}
async function analyze(request: AnalysisRequest, refreshing = false) {
  if (busy.value || (!refreshing && (!selectedInstrument.value || !capabilities.value))) return
  const token = ++analysisToken
  busy.value = true; state.value = 'loading'; message.value = ''
  const analyzedInstrument = refreshing ? lastInstrument : selectedInstrument.value
  lastRequest.value = { ...request }
  lastInstrument = analyzedInstrument
  analyzedName.value = analyzedInstrument?.name ?? request.instrument
  analyzedPeriod.value = request.period
  try {
    if (refreshing) {
      for (const panel of charts.value) {
        if (!panel.request) continue
        panel.state = 'loading'
        panel.message = ''
      }
    } else {
      charts.value = buildChartRequests(request, capabilities.value!.periods, selectedInstrument.value!.kind)
        .map(chart => ({ ...chart, response: null, state: chart.request ? 'loading' : 'empty' }))
    }
  } catch {
    charts.value = []; busy.value = false; state.value = 'error'; message.value = '无法计算图表时间范围，请检查开始和结束日期'
    return
  }
  await Promise.all(charts.value.map(async (panel) => {
    if (!panel.request) return
    try {
      let response: ChartResponse
      try {
        response = await analyzeChart(panel.request)
      } catch (error) {
        if (token !== analysisToken) return
        const first = error instanceof ApiError ? error.firstAvailable : undefined
        if (panel.period === request.period || !(error instanceof ApiError) || error.code !== 'DATE_RANGE_UNAVAILABLE' ||
          !first || !/^\d{4}-\d{2}-\d{2}$/.test(first) || !Number.isFinite(Date.parse(first)) ||
          first <= panel.request.begin_time || first > panel.request.end_time) throw error
        panel.request = { ...panel.request, begin_time: first }
        panel.message = `已按可用历史缩短范围：从 ${first} 开始`
        response = await analyzeChart(panel.request)
      }
      if (token !== analysisToken) return
      if (refreshing && panel.response && !response.candles.length) throw new Error('刷新未返回数据，已保留上次图表')
      panel.response = response
      panel.state = response.candles.length ? 'idle' : 'empty'
      if (panel.period === request.period && response.candles.length && analyzedInstrument) recentInstruments.value = rememberInstrument(analyzedInstrument)
    } catch (error) {
      if (token !== analysisToken) return
      panel.state = error instanceof ApiError && error.code === 'NO_DATA' ? 'empty' : 'error'
      panel.message = `${refreshing && panel.response ? '刷新失败，保留上次图表：' : ''}${(error as Error).message}`
    }
  }))
  if (token === analysisToken) { busy.value = false; state.value = 'idle' }
}
</script>
<template>
  <div class="app-shell"><header class="topbar"><div class="brand-mark">缠</div><div><strong>缠论图表</strong><span>LOCAL MARKET ANALYSIS</span></div><div class="local-badge"><i></i> 本机运行</div></header>
    <main><section class="hero"><div><p class="eyebrow">A-SHARE MARKET · CHAN THEORY</p><h1>让走势结构，<br/><em>清晰可见。</em></h1><p class="hero-description">选择标的与时间范围，探索 K 线、笔、线段、中枢和买卖点。</p></div><div class="hero-art"><div class="art-grid"></div><div class="art-line"></div><span>走势 · 结构 · 决策</span></div></section>
      <section class="workbench"><div class="section-heading"><div><p class="eyebrow">WORKSPACE / 01</p><h2>行情分析</h2></div><span class="section-note">数据时间 · Asia/Shanghai</span></div>
        <QueryForm :capabilities="capabilities" :selected-instrument="selectedInstrument" :suggestions="suggestions" :recent-instruments="recentInstruments" :busy="busy" @search="search" @pick="pick" @clear="clear" @submit="analyze" />
        <div class="result-panel"><div class="result-heading"><div><span class="result-kicker">CHART VIEW</span><h3>{{ charts.length ? analyzedName : '缠论结构图' }}</h3></div><div v-if="charts.length" class="result-actions"><span class="result-meta">三级别分析 · {{ analyzedPeriod }}</span><button type="button" class="refresh-button" :disabled="busy" @click="refresh">{{ busy ? '刷新中…' : '刷新' }}</button></div></div>
          <ChartStatus v-if="!charts.length" :state="state" :message="message" />
          <template v-else>
            <LayerToggles v-model="visibleLayers" />
            <section v-for="(panel, index) in charts" :key="panel.period" class="period-panel" :class="{ 'selected-period': panel.period === analyzedPeriod }" :aria-label="`${panel.period} 图表`">
              <div class="result-heading"><div><h4>{{ panel.period }} · {{ ['低一级别', '所选周期', '高一级别'][index] }}</h4><p v-if="panel.request" class="period-range">分析范围：{{ panel.request.begin_time }} 至 {{ panel.request.end_time }}</p></div>
                <span v-if="panel.response?.candles.length" class="result-meta">{{ panel.response.meta.bar_count }} 根 K 线 · {{ panel.response.meta.source }}<br/>{{ panel.response.meta.first_bar.replace('T', ' ').slice(0, 16) }} 至 {{ panel.response.meta.last_bar.replace('T', ' ').slice(0, 16) }}</span>
              </div>
              <p v-if="panel.response && panel.message" class="period-range">{{ panel.message }}</p>
              <DataFreshness v-if="panel.response" :meta="panel.response.meta" />
              <ChartView v-if="panel.response" :response="panel.response" :visible-layers="visibleLayers" />
              <ChartStatus v-else :state="panel.state" :message="panel.message" />
            </section>
          </template>
        </div>
      </section></main><footer>CHAN.PY · PERSONAL MARKET WORKSPACE</footer></div>
</template>
