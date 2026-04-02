import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'

import ForgotPassword from '../../src/views/ForgotPassword.vue'
import ResetPasswordConfirm from '../../src/views/ResetPasswordConfirm.vue'
import Login from '../../src/views/Login.vue'

const { mockPost, mockPush } = vi.hoisted(() => ({
  mockPost: vi.fn(),
  mockPush: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
  useRoute: () => ({ query: { uid: 'abc', token: 'valid-token' } }),
}))

vi.mock('../../src/services/api', () => ({
  default: { post: mockPost },
}))

vi.mock('../../src/stores/auth', () => ({
  useAuthStore: () => ({
    lastError: '',
    clearError: vi.fn(),
    login: vi.fn(),
    user: null,
  }),
}))

describe('Password reset views', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('submits forgot password request and shows generic message', async () => {
    mockPost.mockResolvedValueOnce({ data: { message: 'Si un compte existe pour cette adresse email, un lien de réinitialisation a été envoyé.' } })

    const wrapper = mount(ForgotPassword, {
      global: { stubs: ['router-link'] },
    })

    await wrapper.get('input[type="email"]').setValue('user@example.com')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(mockPost).toHaveBeenCalledWith('/password-reset/', { email: 'user@example.com' })
    expect(wrapper.text()).toContain('Si un compte existe')
  })

  it('validates reset password minimum length before API call', async () => {
    const wrapper = mount(ResetPasswordConfirm)

    const inputs = wrapper.findAll('input[type="password"]')
    await inputs[0].setValue('short')
    await inputs[1].setValue('short')
    await wrapper.get('form').trigger('submit.prevent')

    expect(mockPost).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('au moins 12 caractères')
  })

  it('renders forgot-password link on login page', () => {
    const wrapper = mount(Login, {
      props: { roleContext: 'Teacher' },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })

    const links = wrapper.findAllComponents(RouterLinkStub)
    expect(links.some((link) => link.props('to') === '/forgot-password')).toBe(true)
  })
})
