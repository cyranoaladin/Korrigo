import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import CorrectorDashboard from '../../src/views/CorrectorDashboard.vue'

const EXAM_TYPE = {
  id: 'type-bac',
  code: 'BAC_BLANC_MATHS_2026',
  name: 'Bac Blanc Maths 2026',
  color: '#2563eb',
  icon: 'graduation-cap',
}

const {
  mockPush,
  mockReplace,
  mockApiGet,
  mockListCopies,
  mockFetchScores,
  mockFetchExamStats,
} = vi.hoisted(() => ({
  mockPush: vi.fn(),
  mockReplace: vi.fn(),
  mockApiGet: vi.fn(() => Promise.resolve({ data: [] })),
  mockListCopies: vi.fn(() => Promise.resolve([])),
  mockFetchScores: vi.fn(() => Promise.resolve({ scores_data: {} })),
  mockFetchExamStats: vi.fn(() => Promise.resolve({ group_stats: [] })),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  useRoute: () => ({ params: {}, query: {} }),
}))

vi.mock('../../src/stores/auth', () => ({
  useAuthStore: () => ({
    user: {
      username: 'prof1',
      role: 'Teacher',
      is_superuser: false,
      features: {
        jury_report_exam_codes: [],
        show_questionnaire: false,
      },
    },
    logout: vi.fn(),
  }),
}))

vi.mock('../../src/services/api', () => ({
  default: {
    get: mockApiGet,
    post: vi.fn(),
    defaults: { baseURL: '/api' },
  },
}))

vi.mock('../../src/services/gradingApi', () => ({
  default: {
    listCopies: mockListCopies,
    fetchScores: mockFetchScores,
    fetchExamStats: mockFetchExamStats,
  },
}))

vi.mock('../../src/components/JuryReportsModal.vue', () => ({
  default: {
    name: 'JuryReportsModal',
    template: '<div data-testid="jury-reports-modal-stub" />',
  },
}))

vi.mock('../../src/components/ExamTypeSelectionModal.vue', () => ({
  default: {
    name: 'ExamTypeSelectionModal',
    props: ['visible'],
    emits: ['select'],
    data() {
      return { examType: EXAM_TYPE }
    },
    template: `
      <button
        v-if="visible"
        data-testid="select-exam-type"
        @click="$emit('select', examType)"
      >
        Select exam type
      </button>
    `,
  },
}))

const AppIcon = { template: '<span class="icon"></span>', props: ['name', 'size'] }

const finalizedCopy = {
  id: 'c1',
  anonymous_id: 'A001',
  status: 'FINALIZED',
  exam: 'exam-1',
  exam_details: {
    id: 'exam-1',
    name: 'Maths J1',
    date: '2026-01-10',
    grading_structure: [{ id: 'q1', label: 'Q1', points: 5 }],
    exam_type_details: { color: '#2563eb', icon: 'graduation-cap' },
  },
}

const baseApiGet = (url: string) => {
  if (url === '/grading/questionnaire/') {
    return Promise.resolve({ data: { has_response: false, summary: { is_available: false } } })
  }
  if (url === '/exams/') {
    return Promise.resolve({
      data: [{
        id: 'exam-1',
        name: 'Maths J1',
        date: '2026-01-10',
        exam_type_details: { color: '#2563eb', icon: 'graduation-cap' },
      }],
    })
  }
  if (url === '/grading/my-students/') {
    return Promise.resolve({ data: { students: [] } })
  }
  return Promise.resolve({ data: [] })
}

const mountDashboard = () => mount(CorrectorDashboard, {
  global: {
    components: { AppIcon },
    stubs: ['RouterLink', 'RouterView'],
  },
})

const selectExamType = async (wrapper: ReturnType<typeof mountDashboard>) => {
  await wrapper.get('[data-testid="select-exam-type"]').trigger('click')
  await flushPromises()
  await flushPromises()
}

describe('CorrectorDashboard - Pronote Export Visibility', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorage.clear()
    mockApiGet.mockImplementation(baseApiGet)
    mockListCopies.mockResolvedValue([finalizedCopy])
    mockFetchScores.mockResolvedValue({ scores_data: { q1: 5 } })
    mockFetchExamStats.mockResolvedValue({ group_stats: [] })
  })

  it('renders the inline Pronote export button for each exam group', async () => {
    const wrapper = mountDashboard()

    await selectExamType(wrapper)

    expect(mockListCopies).toHaveBeenCalledWith({ exam_type_id: EXAM_TYPE.id })
    expect(wrapper.findAll('.btn-export-inline')).toHaveLength(1)
    expect(wrapper.get('.btn-export-inline').text()).toContain('Export')
  })

  it('renders the CSV export button in the stats table when group stats exist', async () => {
    mockFetchExamStats.mockResolvedValue({
      exam_id: 'exam-1',
      exam_name: 'Maths J1',
      global_stats: { mean: 10, median: 10, count: 20 },
      lot_stats: { mean: 11, median: 11, count: 1, std_dev: 0, min: 11, max: 11 },
      all_graded: true,
      graded_copies: 1,
      total_copies: 1,
      lot_distribution: [],
      global_distribution: [],
      group_stats: [
        {
          groupe: 'G1',
          mean: 12,
          median: 12,
          std_dev: 0,
          min: 12,
          max: 12,
          count: 10,
          above_mean: 5,
          below_mean: 5,
          type: 'groupe',
        },
      ],
    })

    const wrapper = mountDashboard()

    await selectExamType(wrapper)

    expect(mockFetchExamStats).toHaveBeenCalledWith('exam-1')
    expect(wrapper.findAll('.btn-export-table')).toHaveLength(1)
    expect(wrapper.get('.btn-export-table').text()).toContain('CSV')
  })
})
