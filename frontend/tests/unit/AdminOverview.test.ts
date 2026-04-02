import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

import AdminOverview from '../../src/views/admin/AdminOverview.vue'

const { mockPush, mockApiGet } = vi.hoisted(() => ({
  mockPush: vi.fn(),
  mockApiGet: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
}))

vi.mock('../../src/stores/auth', () => ({
  useAuthStore: () => ({
    user: { username: 'admin_test', role: 'Admin' },
  }),
}))

vi.mock('../../src/services/api', () => ({
  default: { get: mockApiGet },
}))

describe('AdminOverview', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads exams and global stats in parallel', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url === '/exams/') {
        return Promise.resolve({ data: [{ id: 'exam-1', name: 'Maths', date: '2026-04-01', copies_count: 2, copies_by_status: { READY: 1, IN_PROGRESS: 1, FINALIZED: 0 } }] })
      }
      if (url === '/exams/global-stats/') {
        return Promise.resolve({
          data: {
            total_exams: 4,
            total_copies: 24,
            copies_by_status: { READY: 3, IN_PROGRESS: 7, FINALIZED: 14 },
            students_count: 120,
            exams_with_results_released: 2,
            correctors_count: 9,
          },
        })
      }
      return Promise.reject(new Error(`Unexpected URL ${url}`))
    })

    const wrapper = mount(AdminOverview)
    await flushPromises()

    expect(mockApiGet).toHaveBeenCalledWith('/exams/')
    expect(mockApiGet).toHaveBeenCalledWith('/exams/global-stats/')
    expect(wrapper.text()).toContain('24')
    expect(wrapper.text()).toContain('120')
    expect(wrapper.text()).toContain('9')
  })
})
