<script setup lang="ts">
defineProps<{ state: 'idle' | 'loading' | 'empty' | 'error'; message?: string }>()
</script>
<template><div class="chart-status" role="status"><div class="status-icon">{{ state === 'loading' ? '◌' : state === 'error' ? '!' : '⌁' }}</div><strong>{{ state === 'idle' ? '选择标的开始分析' : state === 'loading' ? '正在计算缠论结构' : state === 'empty' ? '没有可显示的数据' : '分析遇到问题' }}</strong><p>{{ message ?? (state === 'idle' ? '选择市场标的、周期与日期范围，然后点击分析图表。' : '') }}</p></div></template>
