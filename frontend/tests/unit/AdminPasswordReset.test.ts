import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

import ExamStudentList from '../../src/views/admin/ExamStudentList.vue'
import UserManagement from '../../src/views/admin/UserManagement.vue'

const { mockApiGet, mockApiPost, mockPush } = vi.hoisted(() => ({
  mockApiGet: vi.fn(),
  mockApiPost: vi.fn(),
  mockPush: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { examId: 'exam-123' } }),
  useRouter: () => ({ push: mockPush }),
}))

vi.mock('../../src/services/api', () => ({
  default: { get: mockApiGet, post: mockApiPost },
}))

describe('admin password reset workflows', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    vi.spyOn(window, 'alert').mockImplementation(() => {})
  })

  it('resets a student password from the exam student list with an application modal and no credential leak', async () => {
    mockApiGet.mockResolvedValue({
      data: {
        summary: {
          exam_name: 'Produit scalaire',
          total_students: 1,
          graded: 0,
          ready: 1,
          staging: 0,
          average: null,
          min_score: null,
          max_score: null,
          has_groups: false,
        },
        copies: [
          {
            student_id: 7,
            student_name: 'Dupont Ali',
            student_class: '1 EDS',
            anonymous_id: '4C9D-001',
            status: 'READY',
            has_copy: true,
            total_score: null,
            corrector: 'alaeddine.benrhouma@ert.tn',
            has_appreciation: false,
          },
        ],
      },
    })
    mockApiPost.mockResolvedValue({
      data: {
        detail: "Mot de passe réinitialisé. L'élève devra le changer à sa prochaine connexion.",
        student_id: 7,
        student_name: 'Ali Dupont',
        must_change_password: true,
      },
    })

    const wrapper = mount(ExamStudentList, {
      global: {
        stubs: {
          AppIcon: true,
          RouterLink: true,
        },
      },
    })
    await flushPromises()

    const resetButton = wrapper.findAll('button').find((button) => button.attributes('title')?.includes('Réinitialiser'))
    expect(resetButton).toBeTruthy()
    await resetButton!.trigger('click')
    await flushPromises()

    expect(window.confirm).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="password-reset-dialog"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Réinitialiser le mot de passe')
    expect(wrapper.text()).toContain('Dupont Ali')

    const confirmButton = wrapper.find('[data-testid="password-reset-confirm"]')
    expect(confirmButton.exists()).toBe(true)
    await confirmButton.trigger('click')
    await flushPromises()

    expect(mockApiPost).toHaveBeenCalledWith('/students/admin/reset-password/', { student_id: 7 })
    expect(window.alert).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Mot de passe réinitialisé avec succès')
    expect(wrapper.text()).not.toContain('new_password')
    expect(wrapper.text()).not.toContain('Nouveau mot de passe')
    expect(wrapper.text()).not.toContain('undefined')
  })

  it('resets an admin-managed user with an application modal and no generated credential display', async () => {
    mockApiGet.mockImplementation((url: string, config?: { params?: { role?: string } }) => {
      if (url === '/students/') {
        return Promise.resolve({ data: [] })
      }
      if (url === '/users/' && config?.params?.role === 'Teacher') {
        return Promise.resolve({
          data: [
            {
              id: 42,
              username: 'prof.maths',
              email: 'prof.maths@example.test',
              is_active: true,
              last_login: null,
            },
          ],
        })
      }
      return Promise.reject(new Error(`Unexpected GET ${url}`))
    })
    mockApiPost.mockResolvedValue({
      data: {
        message: "Mot de passe réinitialisé. L'utilisateur devra le changer à sa prochaine connexion.",
      },
    })

    const wrapper = mount(UserManagement, {
      global: {
        stubs: {
          AppIcon: true,
        },
      },
    })
    await flushPromises()

    const teachersTab = wrapper.findAll('button').find((button) => button.text().includes('Enseignants'))
    expect(teachersTab).toBeTruthy()
    await teachersTab!.trigger('click')
    await flushPromises()

    const resetButton = wrapper.findAll('button').find((button) => button.text().includes('Réinitialiser'))
    expect(resetButton).toBeTruthy()
    await resetButton!.trigger('click')
    await flushPromises()

    expect(window.confirm).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="password-reset-dialog"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('prof.maths')

    const confirmButton = wrapper.find('[data-testid="password-reset-confirm"]')
    expect(confirmButton.exists()).toBe(true)
    await confirmButton.trigger('click')
    await flushPromises()

    expect(mockApiPost).toHaveBeenCalledWith('/users/42/reset-password/')
    expect(window.alert).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Mot de passe réinitialisé avec succès')
    expect(wrapper.text()).not.toContain('temporary_password')
    expect(wrapper.text()).not.toContain('password')
    expect(wrapper.text()).not.toContain('undefined')
  })
})
