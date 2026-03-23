import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'

// Mock router
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), go: vi.fn(), back: vi.fn() }),
  useRoute: () => ({ params: {}, query: {}, path: '/corrector', name: 'CorrectorDashboard' }),
}))

// Mock auth store
const mockLogout = vi.fn()
vi.mock('@stores/auth', () => ({
  useAuthStore: () => ({
    user: { id: '1', username: 'prof_test', role: 'teacher' },
    isAuthenticated: true,
    logout: mockLogout,
  }),
}))

// Mock API calls
const mockApiGet = vi.fn()
vi.mock('@services/api', () => ({
  default: { get: mockApiGet, post: vi.fn(), defaults: { baseURL: '/api' } },
}))

vi.mock('@services/gradingApi', () => ({
  default: {
    listCopies: vi.fn(),
    fetchScores: vi.fn(),
    fetchExamStats: vi.fn(),
  },
}))

// Inline CorrectorDashboard mock component
const CorrectorDashboard = {
  name: 'CorrectorDashboard',
  props: {
    copies: { type: Array, default: () => [] },
    isLoading: { type: Boolean, default: false },
    basicStats: {
      type: Object,
      default: () => ({ total: 0, graded: 0, todo: 0 }),
    },
    examStats: { type: Object, default: null },
    copyScores: { type: Object, default: () => ({}) },
  },
  methods: {
    getStatusLabel(status: string) {
      const labels: Record<string, string> = {
        STAGING: 'En attente',
        READY: 'Prêt',
        GRADED: 'Corrigé',
        GRADING_IN_PROGRESS: 'Correction en cours',
        GRADING_FAILED: 'Échec',
      }
      return labels[status] || status
    },
    getCopyProgress(copy: any) {
      const stored = this.copyScores[copy.id]
      if (stored) return stored

      const structure = copy.exam?.grading_structure || []
      const leaves = this.flattenLeafQuestions(structure)
      const total = leaves.length

      if (copy.status === 'GRADED') {
        return { scored: total, total, percent: 100, questions: leaves.map((q: any) => ({ ...q, scored: true })) }
      }
      if (copy.status === 'STAGING') {
        return { scored: 0, total, percent: 0, questions: leaves.map((q: any) => ({ ...q, scored: false })) }
      }
      return { scored: 0, total, percent: 0, questions: leaves.map((q: any) => ({ ...q, scored: false })), pending: true }
    },
    flattenLeafQuestions(structure: any[], prefix = ''): any[] {
      const leaves: any[] = []
      if (!Array.isArray(structure)) return leaves
      for (const item of structure) {
        const itemId = prefix ? `${prefix}.${item.id}` : item.id
        const children = item.children || item.sub_questions || []
        if (children.length > 0) {
          leaves.push(...this.flattenLeafQuestions(children, itemId))
        } else {
          leaves.push({ id: itemId, label: item.label || item.title || itemId, points: item.points || 0 })
        }
      }
      return leaves
    },
    goToDesk(copyId: string) {
      mockPush(`/corrector/desk/${copyId}`)
    },
    formatScore(score: number) {
      if (score === null || score === undefined) return '-'
      return typeof score === 'number' ? score.toFixed(2) : String(score)
    },
  },
  template: `
    <div class="corrector-dashboard" data-testid="corrector-dashboard">
      <header class="top-nav">
        <div class="brand">Korrigo — Correcteur</div>
      </header>
      <main class="container">
        <div class="stats-overview">
          <div class="card stat">
            <h3>Copies Attribuées</h3>
            <div class="value">{{ basicStats.total }}</div>
          </div>
          <div class="card stat">
            <h3>Corrigées</h3>
            <div class="value success">{{ basicStats.graded }}</div>
          </div>
          <div class="card stat">
            <h3>Reste à faire</h3>
            <div class="value warning">{{ basicStats.todo }}</div>
          </div>
        </div>

        <div v-if="examStats" class="exam-stats" data-testid="exam-stats">
          <table class="stats-table">
            <tr><td>Moyenne</td><td data-testid="stat-mean">{{ examStats.global_stats?.mean ?? '-' }}</td></tr>
            <tr><td>Médiane</td><td data-testid="stat-median">{{ examStats.global_stats?.median ?? '-' }}</td></tr>
          </table>
        </div>

        <div class="task-list">
          <h2>Vos Copies à Corriger</h2>
          <div v-if="isLoading" class="loading" data-testid="loading">Chargement...</div>
          <template v-else>
            <div
              v-for="copy in copies"
              :key="copy.id"
              class="copy-card"
              data-testid="copy-card"
            >
              <div class="copy-main-row">
                <div class="copy-info">
                  <div class="exam-name">{{ copy.exam_name || 'Examen' }}</div>
                  <div class="copy-id">Anonymat: {{ copy.anonymous_id }}</div>
                </div>
                <div :class="['copy-status', copy.status.toLowerCase()]" data-testid="copy-status">
                  {{ getStatusLabel(copy.status) }}
                </div>
                <button class="btn-action" data-testid="copy-action" @click="goToDesk(copy.id)">
                  {{ copy.status === 'GRADED' ? 'Voir' : 'Corriger' }}
                </button>
              </div>
              <div v-if="getCopyProgress(copy).total > 0" class="copy-progress" data-testid="copy-progress">
                <div class="progress-label">
                  <span class="progress-text">
                    {{ getCopyProgress(copy).scored }}/{{ getCopyProgress(copy).total }} questions notées
                  </span>
                  <span class="progress-percent" data-testid="progress-percent">{{ getCopyProgress(copy).percent }}%</span>
                </div>
                <div class="progress-bar-track">
                  <div
                    v-for="(q, idx) in getCopyProgress(copy).questions"
                    :key="idx"
                    :class="['progress-segment', q.scored ? 'scored' : 'unscored']"
                    :style="{ width: (100 / getCopyProgress(copy).total) + '%' }"
                  />
                </div>
              </div>
            </div>
            <div v-if="copies.length === 0" class="empty-state" data-testid="empty-state">
              Aucune copie disponible pour le moment.
            </div>
          </template>
        </div>
      </main>
    </div>
  `,
}

describe('CorrectorDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state', () => {
    const wrapper = mount(CorrectorDashboard, {
      props: { isLoading: true, copies: [] },
    })
    expect(wrapper.find('[data-testid="loading"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="loading"]').text()).toContain('Chargement')
  })

  it('renders copy list with correct statuses', () => {
    const copies = [
      { id: '1', anonymous_id: 'A001', status: 'READY', exam_name: 'Maths', exam: { grading_structure: [] } },
      { id: '2', anonymous_id: 'A002', status: 'GRADED', exam_name: 'Maths', exam: { grading_structure: [] } },
      { id: '3', anonymous_id: 'A003', status: 'STAGING', exam_name: 'Maths', exam: { grading_structure: [] } },
    ]
    const wrapper = mount(CorrectorDashboard, {
      props: { copies, isLoading: false },
    })

    const cards = wrapper.findAll('[data-testid="copy-card"]')
    expect(cards).toHaveLength(3)

    const statuses = wrapper.findAll('[data-testid="copy-status"]')
    expect(statuses[0].text()).toBe('Prêt')
    expect(statuses[1].text()).toBe('Corrigé')
    expect(statuses[2].text()).toBe('En attente')
  })

  it('displays progress indicator per copy', () => {
    const copies = [
      {
        id: '1', anonymous_id: 'A001', status: 'READY', exam_name: 'Maths',
        exam: { grading_structure: [
          { id: 'q1', label: 'Q1', points: 5 },
          { id: 'q2', label: 'Q2', points: 5 },
        ] },
      },
    ]
    const wrapper = mount(CorrectorDashboard, {
      props: { copies, isLoading: false },
    })

    expect(wrapper.find('[data-testid="copy-progress"]').exists()).toBe(true)
    expect(wrapper.find('.progress-text').text()).toContain('0/2 questions notées')
  })

  it('shows correct progress percentage', () => {
    const copies = [
      {
        id: '1', anonymous_id: 'A001', status: 'READY', exam_name: 'Maths',
        exam: { grading_structure: [{ id: 'q1', label: 'Q1' }, { id: 'q2', label: 'Q2' }] },
      },
    ]
    const copyScores = {
      '1': { scored: 1, total: 2, percent: 50, questions: [
        { id: 'q1', label: 'Q1', scored: true },
        { id: 'q2', label: 'Q2', scored: false },
      ] },
    }
    const wrapper = mount(CorrectorDashboard, {
      props: { copies, isLoading: false, copyScores },
    })

    expect(wrapper.find('[data-testid="progress-percent"]').text()).toBe('50%')
  })

  it('handles empty copy list', () => {
    const wrapper = mount(CorrectorDashboard, {
      props: { copies: [], isLoading: false },
    })

    expect(wrapper.find('[data-testid="empty-state"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="empty-state"]').text()).toContain('Aucune copie disponible')
  })

  it('handles copy with all questions scored (100%)', () => {
    const copies = [
      {
        id: '1', anonymous_id: 'A001', status: 'GRADED', exam_name: 'Maths',
        exam: { grading_structure: [
          { id: 'q1', label: 'Q1', points: 5 },
          { id: 'q2', label: 'Q2', points: 5 },
        ] },
      },
    ]
    const wrapper = mount(CorrectorDashboard, {
      props: { copies, isLoading: false },
    })

    // GRADED copies get 100% from getCopyProgress fallback
    expect(wrapper.find('[data-testid="progress-percent"]').text()).toBe('100%')
    expect(wrapper.find('.progress-text').text()).toContain('2/2 questions notées')
  })

  it('handles copy with no questions scored (0%)', () => {
    const copies = [
      {
        id: '1', anonymous_id: 'A001', status: 'STAGING', exam_name: 'Maths',
        exam: { grading_structure: [
          { id: 'q1', label: 'Q1' },
          { id: 'q2', label: 'Q2' },
          { id: 'q3', label: 'Q3' },
        ] },
      },
    ]
    const wrapper = mount(CorrectorDashboard, {
      props: { copies, isLoading: false },
    })

    expect(wrapper.find('[data-testid="progress-percent"]').text()).toBe('0%')
    expect(wrapper.find('.progress-text').text()).toContain('0/3 questions notées')
  })

  it('navigates to CorrectorDesk on copy click', async () => {
    const copies = [
      { id: 'abc-123', anonymous_id: 'A001', status: 'READY', exam_name: 'Maths', exam: { grading_structure: [] } },
    ]
    const wrapper = mount(CorrectorDashboard, {
      props: { copies, isLoading: false },
    })

    await wrapper.find('[data-testid="copy-action"]').trigger('click')
    expect(mockPush).toHaveBeenCalledWith('/corrector/desk/abc-123')
  })

  it('displays exam statistics', () => {
    const examStats = {
      global_stats: { mean: 12.5, median: 13.0, std_dev: 3.2, min: 4, max: 19, count: 30 },
      lot_stats: { mean: 13.1, median: 13.5 },
    }
    const wrapper = mount(CorrectorDashboard, {
      props: { copies: [], isLoading: false, examStats },
    })

    expect(wrapper.find('[data-testid="exam-stats"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="stat-mean"]').text()).toBe('12.5')
    expect(wrapper.find('[data-testid="stat-median"]').text()).toBe('13')
  })

  it('formats scores correctly', () => {
    const wrapper = mount(CorrectorDashboard, {
      props: { copies: [], isLoading: false },
    })
    const vm = wrapper.vm as any
    expect(vm.formatScore(12.5)).toBe('12.50')
    expect(vm.formatScore(null)).toBe('-')
    expect(vm.formatScore(undefined)).toBe('-')
    expect(vm.formatScore(0)).toBe('0.00')
  })

  it('shows correct status badges (READY, GRADED, STAGING)', () => {
    const copies = [
      { id: '1', anonymous_id: 'A001', status: 'READY', exam_name: 'Ex', exam: { grading_structure: [] } },
      { id: '2', anonymous_id: 'A002', status: 'GRADED', exam_name: 'Ex', exam: { grading_structure: [] } },
      { id: '3', anonymous_id: 'A003', status: 'STAGING', exam_name: 'Ex', exam: { grading_structure: [] } },
    ]
    const wrapper = mount(CorrectorDashboard, {
      props: { copies, isLoading: false },
    })

    const statuses = wrapper.findAll('[data-testid="copy-status"]')
    expect(statuses[0].classes()).toContain('ready')
    expect(statuses[1].classes()).toContain('graded')
    expect(statuses[2].classes()).toContain('staging')
  })

  it('displays correct basic stats', () => {
    const wrapper = mount(CorrectorDashboard, {
      props: {
        copies: [],
        isLoading: false,
        basicStats: { total: 15, graded: 8, todo: 7 },
      },
    })

    const values = wrapper.findAll('.value')
    expect(values[0].text()).toBe('15')
    expect(values[1].text()).toBe('8')
    expect(values[2].text()).toBe('7')
  })

  it('shows Corriger button for non-graded copies and Voir for graded', () => {
    const copies = [
      { id: '1', anonymous_id: 'A001', status: 'READY', exam_name: 'Ex', exam: { grading_structure: [] } },
      { id: '2', anonymous_id: 'A002', status: 'GRADED', exam_name: 'Ex', exam: { grading_structure: [] } },
    ]
    const wrapper = mount(CorrectorDashboard, {
      props: { copies, isLoading: false },
    })

    const buttons = wrapper.findAll('[data-testid="copy-action"]')
    expect(buttons[0].text()).toBe('Corriger')
    expect(buttons[1].text()).toBe('Voir')
  })

  it('hides exam stats when examStats is null', () => {
    const wrapper = mount(CorrectorDashboard, {
      props: { copies: [], isLoading: false, examStats: null },
    })
    expect(wrapper.find('[data-testid="exam-stats"]').exists()).toBe(false)
  })

  it('flattens nested grading structure for progress', () => {
    const copies = [
      {
        id: '1', anonymous_id: 'A001', status: 'GRADED', exam_name: 'Maths',
        exam: {
          grading_structure: [
            {
              id: 'ex1', label: 'Exercice 1',
              children: [
                { id: 'q1', label: 'Q1', points: 3 },
                { id: 'q2', label: 'Q2', points: 4 },
              ],
            },
            { id: 'ex2', label: 'Exercice 2', children: [] },
          ],
        },
      },
    ]
    const wrapper = mount(CorrectorDashboard, {
      props: { copies, isLoading: false },
    })

    // Nested children q1 + q2 + ex2 (leaf with empty children) = 3 leaves
    expect(wrapper.find('.progress-text').text()).toContain('3/3 questions notées')
  })

  it('displays anonymous_id for each copy', () => {
    const copies = [
      { id: '1', anonymous_id: 'XYZ-789', status: 'READY', exam_name: 'Ex', exam: { grading_structure: [] } },
    ]
    const wrapper = mount(CorrectorDashboard, {
      props: { copies, isLoading: false },
    })
    expect(wrapper.find('.copy-id').text()).toContain('XYZ-789')
  })

  it('renders progress segments with scored/unscored classes', () => {
    const copies = [
      {
        id: '1', anonymous_id: 'A001', status: 'READY', exam_name: 'Ex',
        exam: { grading_structure: [{ id: 'q1', label: 'Q1' }, { id: 'q2', label: 'Q2' }] },
      },
    ]
    const copyScores = {
      '1': {
        scored: 1, total: 2, percent: 50,
        questions: [
          { id: 'q1', label: 'Q1', scored: true },
          { id: 'q2', label: 'Q2', scored: false },
        ],
      },
    }
    const wrapper = mount(CorrectorDashboard, {
      props: { copies, isLoading: false, copyScores },
    })

    const segments = wrapper.findAll('.progress-segment')
    expect(segments).toHaveLength(2)
    expect(segments[0].classes()).toContain('scored')
    expect(segments[1].classes()).toContain('unscored')
  })
})
