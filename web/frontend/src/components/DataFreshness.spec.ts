import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import DataFreshness from './DataFreshness.vue'

it('distinguishes forming bars from confirmed candles and shows the actual fetch time', () => {
  const wrapper = mount(DataFreshness, { props: { meta: { data_status: 'live', fetched_at: '2026-09-24T10:05:00+08:00', provisional_count: 1, warnings: [] } } })
  expect(wrapper.text()).toContain('盘中行情')
  expect(wrapper.text()).toContain('10:05:00')
  expect(wrapper.text()).toContain('1 根未收盘')
  expect(wrapper.text()).toContain('结构与买卖点可能变化')
})

it('shows delayed-data warnings instead of presenting a failed update as live', () => {
  const wrapper = mount(DataFreshness, { props: { meta: { data_status: 'delayed', fetched_at: '2026-09-24T09:55:00+08:00', provisional_count: 0, warnings: ['盘中更新失败，当前显示上次成功获取的数据'] } } })
  expect(wrapper.text()).toContain('延迟行情')
  expect(wrapper.text()).toContain('上次成功获取')
  expect(wrapper.text()).not.toContain('根未收盘')
})
