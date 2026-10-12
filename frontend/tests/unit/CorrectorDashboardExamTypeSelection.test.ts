import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import CorrectorDashboard from '../../src/views/CorrectorDashboard.vue'

const { mockApiGet, mockListCopies, mockLogout, mockPush } = vi.hoisted(() => ({
  mockApiGet: vi.fn(),
  mockListCopies: vi.fn(),
  mockLogout: vi.fn(),
  mockPush: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn() }),
}))

vi.mock('../../src/stores/auth', () => ({
  useAuthStore: () => ({
    user: { username: 'prof_without_assignments', role: 'Teacher', features: {} },
    logout: mockLogout,
  }),
}))

vi.mock('../../src/services/api', () => ({
  default: { get: mockApiGet, post: vi.fn(), defaults: { baseURL: '/api' } },
}))

vi.mock('../../src/services/gradingApi', () => ({
  default: { listCopies: mockListCopies },
}))

const MATHS = { id: 'maths', name: 'Mathématiques', color: '#2563eb', icon: 'calculator' }
const PHYSICS = { id: 'physics', name: 'Physique', color: '#16a34a', icon: 'atom' }

const mountDashboard = () => mount(CorrectorDashboard, {
  global: {
    stubs: { JuryReportsModal: true, ExamTypeIcon: true, AppIcon: true },
  },
})

let wrapper: ReturnType<typeof mountDashboard>

describe('Corrector dashboard exam type selection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    vi.mocked(localStorage.getItem).mockReturnValue(null)
    mockApiGet.mockResolvedValue({ data: [] })
    mockListCopies.mockResolvedValue([])
    mockLogout.mockResolvedValue(undefined)
  })

  afterEach(() => {
    wrapper?.unmount()
    vi.restoreAllMocks()
  })

  it.each([
    { label: 'an empty array', types: [] },
    { label: 'an empty paginated list', types: { results: [] } },
  ])('shows an empty dashboard and permits logout for $label', async ({ types }) => {
    mockApiGet.mockResolvedValue({ data: types })
    wrapper = mountDashboard()

    await flushPromises()

    expect(wrapper.find('[data-testid="exam-type-selection-modal"]').exists()).toBe(false)
    expect(wrapper.get('.task-list .empty-state').text()).toBe('Aucune copie disponible pour le moment.')
    expect(wrapper.find('.task-list .loading').exists()).toBe(false)
    expect(mockListCopies).not.toHaveBeenCalled()
    expect(localStorage.setItem).not.toHaveBeenCalled()

    await wrapper.get('[data-testid="logout-button"]').trigger('click')
    await flushPromises()

    expect(mockLogout).toHaveBeenCalledOnce()
    expect(mockPush).toHaveBeenCalledWith('/')
  })

  it('keeps the modal while types are loading', async () => {
    mockApiGet.mockReturnValue(new Promise(() => {}))
    wrapper = mountDashboard()

    await flushPromises()

    expect(wrapper.get('[data-testid="exam-type-selection-modal"]').text()).toContain('Chargement des matières disponibles')
    expect(wrapper.find('.task-list .empty-state').exists()).toBe(false)
    expect(mockListCopies).not.toHaveBeenCalled()
  })

  it('keeps API failures distinct from a successful empty response', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    mockApiGet.mockRejectedValue(new Error('Network unavailable'))
    wrapper = mountDashboard()

    await flushPromises()

    expect(wrapper.get('[data-testid="exam-type-selection-modal"] .error-state').text()).toBe("Impossible de charger les types d'examens.")
    expect(wrapper.find('.task-list .empty-state').exists()).toBe(false)
    expect(mockListCopies).not.toHaveBeenCalled()
  })

  it('preserves automatic selection when exactly one type is available', async () => {
    mockApiGet.mockImplementation((url: string) => Promise.resolve({ data: url === '/exams/types/' ? [MATHS] : [] }))
    wrapper = mountDashboard()

    await flushPromises()

    expect(wrapper.find('[data-testid="exam-type-selection-modal"]').exists()).toBe(false)
    expect(mockListCopies).toHaveBeenCalledWith({ exam_type_id: MATHS.id })
    expect(wrapper.get('.type-badge').text()).toBe(MATHS.name)
  })

  it('requires selection when multiple types are available', async () => {
    mockApiGet.mockImplementation((url: string) => Promise.resolve({ data: url === '/exams/types/' ? [MATHS, PHYSICS] : [] }))
    wrapper = mountDashboard()

    await flushPromises()

    expect(wrapper.find('[data-testid="exam-type-selection-modal"]').exists()).toBe(true)
    expect(wrapper.findAll('.type-card')).toHaveLength(2)
    expect(mockListCopies).not.toHaveBeenCalled()

    await wrapper.get('.type-card').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="exam-type-selection-modal"]').exists()).toBe(false)
    expect(mockListCopies).toHaveBeenCalledWith({ exam_type_id: MATHS.id })
  })
})
