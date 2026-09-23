<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { AnalysisRequest, CapabilityResponse, InstrumentOption } from '../api/types'
const props = defineProps<{ capabilities: CapabilityResponse | null; selectedInstrument: InstrumentOption | null; busy: boolean; suggestions?: InstrumentOption[] }>()
const emit = defineEmits<{ (e: 'submit', request: AnalysisRequest): void; (e: 'search', query: string): void; (e: 'pick', option: InstrumentOption): void; (e: 'clear'): void }>()
const today = new Date()
const end = ref(today.toISOString().slice(0, 10))
const start = ref(new Date(today.getTime() - 90 * 86400000).toISOString().slice(0, 10))
const search = ref('')
const period = ref('')
const adjustment = ref('')
const options = computed(() => (props.capabilities?.periods ?? []).filter(item =>
  props.selectedInstrument && item.kind === props.selectedInstrument.kind &&
  (!item.instrument || item.instrument === props.selectedInstrument.instrument)))
const periods = computed(() => [...new Set(options.value.map(item => item.period))])
const adjustments = computed(() => options.value.find(item => item.period === period.value)?.adjustments ?? [])
watch(periods, value => { if (!value.includes(period.value)) period.value = value[0] ?? '' }, { immediate: true })
watch(adjustments, value => { if (!value.includes(adjustment.value)) adjustment.value = value[0] ?? '' }, { immediate: true })
const canSubmit = computed(() => !!props.selectedInstrument && !!period.value && !!adjustment.value &&
  start.value <= end.value && !props.busy)
function submit() {
  if (!canSubmit.value || !props.selectedInstrument) return
  emit('submit', { market: 'cn', instrument: props.selectedInstrument.instrument, period: period.value,
    begin_time: start.value, end_time: end.value, adjustment: adjustment.value })
}
function pick(option: InstrumentOption) { search.value = ''; emit('pick', option) }
</script>
<template>
  <form class="query-form" @submit.prevent="submit">
    <div class="field instrument-field">
      <label for="instrument-search">标的</label>
      <div v-if="selectedInstrument" class="selected-instrument"><span>{{ selectedInstrument.name }} <small>{{ selectedInstrument.instrument }}</small></span><button type="button" @click="emit('clear')">更换</button></div>
      <template v-else>
        <input id="instrument-search" v-model="search" autocomplete="off" placeholder="输入代码或名称，如 000001" @input="emit('search', search)" />
        <ul v-if="suggestions?.length" class="suggestions"><li v-for="option in suggestions" :key="option.instrument"><button type="button" @click="pick(option)">{{ option.name }} <small>{{ option.instrument }}</small></button></li></ul>
      </template>
    </div>
    <div class="field"><label for="period">周期</label><select id="period" v-model="period" :disabled="!selectedInstrument"><option v-for="item in periods" :key="item" :value="item">{{ item }}</option></select></div>
    <div class="field"><label for="adjustment">复权</label><select id="adjustment" v-model="adjustment" :disabled="!selectedInstrument"><option v-for="item in adjustments" :key="item" :value="item">{{ item === 'none' ? '不复权' : item }}</option></select></div>
    <div class="field"><label for="begin_time">开始日期</label><input id="begin_time" v-model="start" name="begin_time" type="date" /></div>
    <div class="field"><label for="end_time">结束日期</label><input id="end_time" v-model="end" name="end_time" type="date" /></div>
    <button class="analyze-button" type="submit" :disabled="!canSubmit">{{ busy ? '分析中…' : '分析图表' }}</button>
    <p v-if="start > end" class="field-error">开始日期不能晚于结束日期</p>
  </form>
</template>
