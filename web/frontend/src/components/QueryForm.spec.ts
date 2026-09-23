import { afterEach, describe, expect, it, vi } from 'vitest'
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
  })
})


afterEach(() => vi.useRealTimers())

describe('quick selections', () => {
  const instrument = { market: 'cn', instrument: 'sh.000001', name: '上证指数', exchange: 'sh', kind: 'index' } as const

  it('picks a previously analyzed instrument without typing a search', async () => {
    const wrapper = mount(QueryForm, { props: { capabilities, selectedInstrument: null, recentInstruments: [instrument], busy: false } })
    await wrapper.get('[aria-label="最近使用的标的"]').get('button').trigger('click')
    expect(wrapper.emitted('pick')?.[0]).toEqual([instrument])
    expect(wrapper.emitted('search')).toBeUndefined()
  })

  it('fills rolling ranges without submitting', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-09-23T02:00:00Z'))
    const wrapper = mount(QueryForm, { props: { capabilities, selectedInstrument: instrument, busy: false } })
    await wrapper.get('button[aria-label="最近30天"]').trigger('click')
    expect((wrapper.get('[name="begin_time"]').element as HTMLInputElement).value).toBe('2026-08-25')
    expect((wrapper.get('[name="end_time"]').element as HTMLInputElement).value).toBe('2026-09-23')
    await wrapper.get('button[aria-label="最近1季度"]').trigger('click')
    expect((wrapper.get('[name="begin_time"]').element as HTMLInputElement).value).toBe('2026-06-24')
    await wrapper.get('button[aria-label="最近1年"]').trigger('click')
    expect((wrapper.get('[name="begin_time"]').element as HTMLInputElement).value).toBe('2025-09-24')
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('clips a shortcut to the provider availability window', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-09-23T02:00:00Z'))
    const bounded = { ...capabilities, periods: [{ ...capabilities.periods[0], first_available: '2026-09-01', last_available: '2026-09-10' }] }
    const wrapper = mount(QueryForm, { props: { capabilities: bounded, selectedInstrument: instrument, busy: false } })
    await wrapper.get('button[aria-label="最近1年"]').trigger('click')
    expect((wrapper.get('[name="begin_time"]').element as HTMLInputElement).value).toBe('2026-09-01')
    expect((wrapper.get('[name="end_time"]').element as HTMLInputElement).value).toBe('2026-09-10')
  })
})


it('does not present the remote Sina fetch limit as a chart limit', () => {
  const sina = { ...capabilities, periods: [{ ...capabilities.periods[0], source: 'sina', first_available: null, last_available: null, max_bars: 1970 }] }
  const instrument = { market: 'cn', instrument: 'sh.000001', name: '上证指数', exchange: 'sh', kind: 'index' } as const
  const wrapper = mount(QueryForm, { props: { capabilities: sina, selectedInstrument: instrument, busy: false } })
  expect(wrapper.text()).not.toContain('单次最多 1970 根 K 线')
})

describe('fund choices', () => {
  it('shows fund type in suggestions and restricts LOF to its daily capability', async () => {
    const lof = { market: 'cn', instrument: 'sz.160706', name: '沪深300LOF', exchange: 'sz', kind: 'lof' } as const
    const fundCapabilities: CapabilityResponse = { market: 'cn', sources: ['sina-lof'], periods: [
      { market: 'cn', source: 'sina-lof', kind: 'lof', period: '1d', adjustments: ['none'], first_available: null, last_available: null, max_bars: 5000, instrument: lof.instrument },
    ] }
    const wrapper = mount(QueryForm, { props: { capabilities: fundCapabilities, selectedInstrument: null, suggestions: [lof], busy: false } })
    expect(wrapper.get('.suggestions .instrument-kind').text()).toBe('LOF')
    await wrapper.get('.suggestions button').trigger('click')
    expect(wrapper.emitted('pick')?.[0]).toEqual([lof])
    await wrapper.setProps({ selectedInstrument: lof })
    expect(wrapper.get('#period').findAll('option').map(x => x.text())).toEqual(['1d'])
    expect(wrapper.get('#adjustment').findAll('option').map(x => x.text())).toEqual(['不复权'])
  })
})
