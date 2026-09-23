<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { analyzeChart, fetchCapabilities, searchInstruments, ApiError } from './api/client'
import type { AnalysisRequest, CapabilityResponse, ChartResponse, InstrumentOption } from './api/types'
import QueryForm from './components/QueryForm.vue'
import { readRecentInstruments, rememberInstrument } from './recentInstruments'
import ChartStatus from './components/ChartStatus.vue'
import ChartView from './chart/ChartView.vue'
import LayerToggles from './components/LayerToggles.vue'
import { allLayersVisible, type LayerVisibility } from './chart/buildChartOption'
const capabilities = ref<CapabilityResponse | null>(null)
const selectedInstrument = ref<InstrumentOption | null>(null)
const suggestions = ref<InstrumentOption[]>([])
const recentInstruments = ref<InstrumentOption[]>([])
const response = ref<ChartResponse | null>(null)
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
function clear() { selectedInstrument.value = null; response.value = null; state.value = 'idle'; void fetchCapabilities('cn').then(value => capabilities.value = value) }
async function analyze(request: AnalysisRequest) {
  if (busy.value) return
  busy.value = true; state.value = 'loading'; message.value = ''
  const analyzedInstrument = selectedInstrument.value?.instrument === request.instrument ? selectedInstrument.value : null
  try {
    response.value = await analyzeChart(request)
    state.value = response.value.candles.length ? 'idle' : 'empty'
    if (response.value.candles.length && analyzedInstrument) recentInstruments.value = rememberInstrument(analyzedInstrument)
  }
  catch (error) { response.value = null; state.value = (error instanceof ApiError && error.code === 'NO_DATA') ? 'empty' : 'error'; message.value = (error as Error).message }
  finally { busy.value = false }
}
</script>
<template>
  <div class="app-shell"><header class="topbar"><div class="brand-mark">缠</div><div><strong>缠论图表</strong><span>LOCAL MARKET ANALYSIS</span></div><div class="local-badge"><i></i> 本机运行</div></header>
    <main><section class="hero"><div><p class="eyebrow">A-SHARE MARKET · CHAN THEORY</p><h1>让走势结构，<br/><em>清晰可见。</em></h1><p class="hero-description">选择标的与时间范围，探索 K 线、笔、线段、中枢和买卖点。</p></div><div class="hero-art"><div class="art-grid"></div><div class="art-line"></div><span>走势 · 结构 · 决策</span></div></section>
      <section class="workbench"><div class="section-heading"><div><p class="eyebrow">WORKSPACE / 01</p><h2>行情分析</h2></div><span class="section-note">数据时间 · Asia/Shanghai</span></div>
        <QueryForm :capabilities="capabilities" :selected-instrument="selectedInstrument" :suggestions="suggestions" :recent-instruments="recentInstruments" :busy="busy" @search="search" @pick="pick" @clear="clear" @submit="analyze" />
        <div class="result-panel"><div class="result-heading"><div><span class="result-kicker">CHART VIEW</span><h3>{{ response ? selectedInstrument?.name : '缠论结构图' }}</h3></div><span v-if="response" class="result-meta">{{ response.meta.bar_count }} 根 K 线 · {{ response.meta.source }}<br/>{{ response.meta.first_bar.replace('T', ' ').slice(0, 16) }} 至 {{ response.meta.last_bar.replace('T', ' ').slice(0, 16) }}</span></div>
          <ChartStatus v-if="!response || state !== 'idle'" :state="state" :message="message" />
          <template v-else><LayerToggles v-model="visibleLayers" /><ChartView :response="response" :visible-layers="visibleLayers" /></template>
        </div>
      </section></main><footer>CHAN.PY · PERSONAL MARKET WORKSPACE</footer></div>
</template>
