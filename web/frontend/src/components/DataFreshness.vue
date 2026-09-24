<script setup lang="ts">
defineProps<{ meta: { data_status?: 'historical' | 'live' | 'delayed'; fetched_at?: string | null; provisional_count?: number; warnings?: string[] } }>()
</script>
<template>
  <div v-if="meta.data_status" class="data-freshness" :class="{ delayed: meta.data_status === 'delayed' }">
    <span>{{ { historical: '历史行情', live: '盘中行情', delayed: '延迟行情' }[meta.data_status] }}</span>
    <span v-if="meta.fetched_at">最近取数：{{ meta.fetched_at.replace('T', ' ').slice(0, 19) }}</span>
    <strong v-if="meta.provisional_count">{{ meta.provisional_count }} 根未收盘 · 结构与买卖点可能变化</strong>
    <p v-for="warning in meta.warnings" :key="warning">{{ warning }}</p>
  </div>
</template>
