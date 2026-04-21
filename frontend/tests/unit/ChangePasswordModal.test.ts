import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

import ChangePasswordModal from '../../src/components/ChangePasswordModal.vue'

const { mockGet, mockPost, mockAuthStore } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
  mockAuthStore: {
    user: { role: 'Student' },
  },
}))

vi.mock('../../src/services/api', () => ({
  default: {
    get: mockGet,
    post: mockPost,
  },
}))

vi.mock('../../src/stores/auth', () => ({
  useAuthStore: () => mockAuthStore,
}))

describe('ChangePasswordModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockAuthStore.user = { role: 'Student' }
    mockGet.mockResolvedValue({ data: { detail: 'Cookie CSRF défini.' } })
  })

  it('fetches a CSRF cookie before submitting a student password change', async () => {
    Object.defineProperty(document, 'cookie', {
      configurable: true,
      get: () => '',
    })
    mockPost.mockResolvedValue({ data: { message: 'ok' } })

    const wrapper = mount(ChangePasswordModal, {
      props: { forced: true },
    })

    await flushPromises()
    expect(mockGet).toHaveBeenCalledWith('/csrf/')

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('01012007')
    await inputs[1].setValue('NouveauMotDePasse2026!')
    await inputs[2].setValue('NouveauMotDePasse2026!')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(mockPost).toHaveBeenCalledWith('/students/change-password/', {
      current_password: '01012007',
      new_password: 'NouveauMotDePasse2026!',
    })
    expect(wrapper.emitted('success')).toBeTruthy()
  })

  it('renders backend detail errors instead of the generic fallback message', async () => {
    Object.defineProperty(document, 'cookie', {
      configurable: true,
      get: () => 'csrftoken=test-token',
    })
    mockPost.mockRejectedValue({
      response: {
        data: {
          detail: 'CSRF token missing or incorrect.',
        },
      },
    })

    const wrapper = mount(ChangePasswordModal, {
      props: { forced: true },
    })

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('01012007')
    await inputs[1].setValue('NouveauMotDePasse2026!')
    await inputs[2].setValue('NouveauMotDePasse2026!')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('CSRF token missing or incorrect.')
    expect(wrapper.text()).not.toContain('Erreur lors du changement de mot de passe.')
  })
})
