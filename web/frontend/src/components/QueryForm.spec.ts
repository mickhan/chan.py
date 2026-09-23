import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import QueryForm from './QueryForm.vue'
import type { CapabilityResponse } from '../api/types'
const capabilities: CapabilityResponse = { market: 'cn', sources: ['fixture'], periods: [{ market: 'cn', source: 'fixture', kind: 'index', period: '30m', adjustments: ['none'], first_available: null, last_available: null, max_bars: 5000, instrument: null }] }

describe('QueryForm', () => {
  it('submits only on explicit click with supported selection', async () => {
    const wrapper = mount(QueryForm, { props: { capabilities, selectedInstrument: { market: 'cn', instrument: 'sh.000001', name: '上证指数', exchange: 'sh', kind: 'index' }, busy: false } })
    expect(wrapper.emitted('submit')).toBeUndefined()
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('submit')).toHaveLength(1)
  })
  it('rejects reversed dates', async () => {
    const wrapper = mount(QueryForm, { props: { capabilities, selectedInstrument: { market: 'cn', instrument: 'sh.000001', name: '上证指数', exchange: 'sh', kind: 'index' }, busy: false } })
    await wrapper.get('[name="begin_time"]').setValue('2026-09-20')
    await wrapper.get('[name="end_time"]').setValue('2026-09-01')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('submit')).toBeUndefined()
  })
})

describe('reported availability', () => {
  it('sets date controls to the selected provider range', async () => {
    const bounded = { ...capabilities, periods: [{ ...capabilities.periods[0], first_available: '2026-09-01', last_available: '2026-09-10', max_bars: 1970 }] }
    const wrapper = mount(QueryForm, { props: { capabilities: bounded, selectedInstrument: { market: 'cn', instrument: 'sh.000001', name: '上证指数', exchange: 'sh', kind: 'index' }, busy: false } })
    expect(wrapper.get('[name="begin_time"]').attributes('min')).toBe('2026-09-01')
    expect(wrapper.get('[name="end_time"]').attributes('max')).toBe('2026-09-10')
    expect(wrapper.text()).toContain('1970')
  })
})
