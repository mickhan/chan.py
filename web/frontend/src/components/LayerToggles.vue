<script setup lang="ts">
import type { LayerVisibility } from '../chart/buildChartOption'
const props = defineProps<{ modelValue: LayerVisibility }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: LayerVisibility): void }>()
const labels: { key: keyof LayerVisibility; text: string }[] = [{ key: 'bi', text: '笔' }, { key: 'segments', text: '线段' }, { key: 'zones', text: '中枢' }, { key: 'buySellPoints', text: '买卖点' }, { key: 'macd', text: 'MACD' }]
function toggle(key: keyof LayerVisibility) { emit('update:modelValue', { ...props.modelValue, [key]: !props.modelValue[key] }) }
</script>
<template><div class="layer-toggles" aria-label="图层开关"><button v-for="item in labels" :key="item.key" type="button" :class="{ active: modelValue[item.key] }" :aria-pressed="modelValue[item.key]" @click="toggle(item.key)">{{ item.text }}</button></div></template>
