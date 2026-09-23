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
