<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { AnalysisRequest, CapabilityResponse, InstrumentOption } from '../api/types'
const props = defineProps<{ capabilities: CapabilityResponse | null; selectedInstrument: InstrumentOption | null; busy: boolean; suggestions?: InstrumentOption[]; recentInstruments?: InstrumentOption[] }>()
const emit = defineEmits<{ (e: 'submit', request: AnalysisRequest): void; (e: 'search', query: string): void; (e: 'pick', option: InstrumentOption): void; (e: 'clear'): void }>()
const today = new Date()
const shanghaiDate = (date: Date) => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(date)
const end = ref(shanghaiDate(today))
const start = ref(shanghaiDate(new Date(today.getTime() - 90 * 86400000)))
const search = ref('')
const period = ref('')
const adjustment = ref('')
const options = computed(() => (props.capabilities?.periods ?? []).filter(item =>
  props.selectedInstrument && item.kind === props.selectedInstrument.kind &&
  (!item.instrument || item.instrument === props.selectedInstrument.instrument)))
const periods = computed(() => [...new Set(options.value.map(item => item.period))])
const currentCapability = computed(() => options.value.find(item => item.period === period.value))
const adjustments = computed(() => currentCapability.value?.adjustments ?? [])
watch(periods, value => { if (!value.includes(period.value)) period.value = value.includes('30m') ? '30m' : value[0] ?? '' }, { immediate: true })
watch(adjustments, value => { if (!value.includes(adjustment.value)) adjustment.value = value[0] ?? '' }, { immediate: true })
watch(currentCapability, value => {
  if (!value) return
  if (value.first_available && start.value < value.first_available) start.value = value.first_available
  if (value.last_available && end.value > value.last_available) end.value = value.last_available
  if (start.value > end.value && value.first_available) start.value = value.first_available
}, { immediate: true })
const canSubmit = computed(() => !!props.selectedInstrument && !!period.value && !!adjustment.value &&
  start.value <= end.value && !props.busy &&
  (!currentCapability.value?.first_available || start.value >= currentCapability.value.first_available) &&
  (!currentCapability.value?.last_available || end.value <= currentCapability.value.last_available))
function submit() {
  if (!canSubmit.value || !props.selectedInstrument) return
  emit('submit', { market: 'cn', instrument: props.selectedInstrument.instrument, period: period.value,
    begin_time: start.value, end_time: end.value, adjustment: adjustment.value })
}
function pick(option: InstrumentOption) { search.value = ''; emit('pick', option) }
function kindLabel(kind: InstrumentOption['kind']) { return ({ stock: '股票', index: '指数', etf: 'ETF', lof: 'LOF' })[kind] }
function dateString(date: Date) { return date.toISOString().slice(0, 10) }
function calendarMonthsAgo(anchor: string, months: number) {
  const [year, month, day] = anchor.split('-').map(Number)
  const first = new Date(Date.UTC(year, month - 1 - months, 1))
  const lastDay = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0)).getUTCDate()
  first.setUTCDate(Math.min(day, lastDay) + 1)
  return dateString(first)
}
function selectRange(range: '30d' | 'quarter' | 'year') {
  const current = shanghaiDate(new Date())
  const availableEnd = currentCapability.value?.last_available
  const chosenEnd = availableEnd && availableEnd < current ? availableEnd : current
  let chosenStart: string
  if (range === '30d') {
    const date = new Date(`${chosenEnd}T00:00:00Z`)
    date.setUTCDate(date.getUTCDate() - 29)
    chosenStart = dateString(date)
  } else {
    chosenStart = calendarMonthsAgo(chosenEnd, range === 'quarter' ? 3 : 12)
  }
  const availableStart = currentCapability.value?.first_available
  start.value = availableStart && chosenStart < availableStart ? availableStart : chosenStart
  end.value = chosenEnd
}
</script>
<template>
  <form class="query-form" @submit.prevent="submit">
    <div class="field instrument-field">
      <label for="instrument-search">标的</label>
      <div v-if="selectedInstrument" class="selected-instrument"><span>{{ selectedInstrument.name }} <small>{{ selectedInstrument.instrument }}</small> <span class="instrument-kind">{{ kindLabel(selectedInstrument.kind) }}</span></span><button type="button" @click="emit('clear')">更换</button></div>
      <template v-else>
        <input id="instrument-search" v-model="search" autocomplete="off" placeholder="输入代码或名称，如 000001" @input="emit('search', search)" />
        <ul v-if="suggestions?.length" class="suggestions"><li v-for="option in suggestions" :key="option.instrument"><button type="button" @click="pick(option)">{{ option.name }} <small>{{ option.instrument }}</small> <span class="instrument-kind">{{ kindLabel(option.kind) }}</span></button></li></ul>
      </template>
    </div>
    <div class="field"><label for="period">周期</label><select id="period" v-model="period" :disabled="!selectedInstrument"><option v-for="item in periods" :key="item" :value="item">{{ item }}</option></select></div>
    <div class="field"><label for="adjustment">复权</label><select id="adjustment" v-model="adjustment" :disabled="!selectedInstrument"><option v-for="item in adjustments" :key="item" :value="item">{{ item === 'none' ? '不复权' : item }}</option></select></div>
    <div class="field"><label for="begin_time">开始日期</label><input id="begin_time" v-model="start" name="begin_time" type="date" :min="currentCapability?.first_available ?? undefined" :max="currentCapability?.last_available ?? undefined" /></div>
    <div class="field"><label for="end_time">结束日期</label><input id="end_time" v-model="end" name="end_time" type="date" :min="currentCapability?.first_available ?? undefined" :max="currentCapability?.last_available ?? undefined" /></div>
    <button class="analyze-button" type="submit" :disabled="!canSubmit">{{ busy ? '分析中…' : '分析图表' }}</button>
    <div class="quick-picks" aria-label="快捷时间范围">
      <span>快速时间</span>
      <button type="button" aria-label="最近30天" :disabled="!currentCapability" @click="selectRange('30d')">最近 30 天</button>
      <button type="button" aria-label="最近1季度" :disabled="!currentCapability" @click="selectRange('quarter')">最近 1 季度</button>
      <button type="button" aria-label="最近1年" :disabled="!currentCapability" @click="selectRange('year')">最近 1 年</button>
    </div>
    <div v-if="!selectedInstrument && !search && recentInstruments?.length" class="quick-picks recent-instruments" aria-label="最近使用的标的">
      <span>最近分析</span>
      <button v-for="option in recentInstruments" :key="option.instrument" type="button" @click="pick(option)">{{ option.name }} <small>{{ option.instrument }}</small> <span class="instrument-kind">{{ kindLabel(option.kind) }}</span></button>
    </div>
    <p v-if="start > end" class="field-error">开始日期不能晚于结束日期</p>
  </form>
</template>
