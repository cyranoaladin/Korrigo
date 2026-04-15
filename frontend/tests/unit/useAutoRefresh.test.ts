import { defineComponent, h, nextTick } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'

import { useAutoRefresh } from '../../src/composables/useAutoRefresh'

describe('useAutoRefresh', () => {
  let visibilityState = 'visible'

  beforeEach(() => {
    vi.useFakeTimers()
    visibilityState = 'visible'
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => visibilityState,
    })
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  it('refreshes immediately, polls, pauses hidden tabs, and resumes on visibility', async () => {
    const refresh = vi.fn().mockResolvedValue(undefined)

    const Harness = defineComponent({
      setup() {
        useAutoRefresh(refresh, { intervalMs: 1000 })
        return () => h('div')
      },
    })

    const wrapper = mount(Harness)
    await flushPromises()
    await nextTick()

    expect(refresh).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(1000)
    await flushPromises()
    expect(refresh).toHaveBeenCalledTimes(2)

    visibilityState = 'hidden'
    document.dispatchEvent(new Event('visibilitychange'))
    await flushPromises()

    await vi.advanceTimersByTimeAsync(2000)
    await flushPromises()
    expect(refresh).toHaveBeenCalledTimes(2)

    visibilityState = 'visible'
    document.dispatchEvent(new Event('visibilitychange'))
    await flushPromises()
    await nextTick()

    expect(refresh).toHaveBeenCalledTimes(3)

    wrapper.unmount()
    await vi.advanceTimersByTimeAsync(2000)
    await flushPromises()
    expect(refresh).toHaveBeenCalledTimes(3)
  })
})
