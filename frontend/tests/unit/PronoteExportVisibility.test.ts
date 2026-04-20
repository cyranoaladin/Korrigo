import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import CorrectorDashboard from '../../src/views/CorrectorDashboard.vue'
import { createPinia, setActivePinia } from 'pinia'

// Use vi.hoisted to avoid ReferenceError
const { mockPush, mockApiGet } = vi.hoisted(() => ({
  mockPush: vi.fn(),
  mockApiGet: vi.fn<any[], any>(() => Promise.resolve({ data: [] })),
}))

// Mock router
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
  useRoute: () => ({ params: {}, query: {} }),
}))

// Mock AppIcon and other global components
const AppIcon = { template: '<span class="icon"></span>', props: ['name'] }

// Mock API
vi.mock('../../src/services/api', () => ({
  default: {
    get: mockApiGet,
    post: vi.fn(),
  }
}))

vi.mock('../../src/services/gradingApi', () => ({
  default: {
    fetchStats: vi.fn(() => Promise.resolve({ group_stats: [] })),
    fetchExamStats: vi.fn(() => Promise.resolve({ group_stats: [] })),
  }
}))

describe('CorrectorDashboard - Pronote Export Visibility', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should render Export Pronote button in exam headers', async () => {
    // Mock API responses for copies
    mockApiGet.mockResolvedValue({
        data: [
            { id: 'c1', anonymous_id: 'A001', status: 'FINALIZED', exam_id: 'exam-1', exam_name: 'Maths J1' }
        ]
    })
    
    const wrapper = mount(CorrectorDashboard, {
      global: {
        components: { AppIcon },
        stubs: ['RouterLink', 'RouterView']
      }
    })

    // Wait for async data
    await new Promise(resolve => setTimeout(resolve, 100))
    
    // Check if Export button exists in the group header
    const exportButtons = wrapper.findAll('.btn-export-inline')
    expect(exportButtons.length).toBeGreaterThan(0)
    expect(exportButtons[0].text()).toContain('Export')
  })

  it('should render CSV export button in the stats table', async () => {
    const examStats = {
        exam_id: 'exam-1',
        exam_name: 'Maths J1',
        global_stats: { mean: 10, median: 10, count: 20 },
        lot_distribution: [],
        global_distribution: [],
        group_stats: [
            { groupe: 'G1', mean: 12, count: 10, above_mean: 5, below_mean: 5, type: 'groupe' }
        ]
    }

    // Mock fetchExamStats which is called by fetchStats/scrollToStats
    const { default: gradingApi } = await import('../../src/services/gradingApi')
    vi.mocked(gradingApi.fetchExamStats).mockResolvedValue(examStats)

    mockApiGet.mockResolvedValue({ data: [{ id: 'c1', exam: 'exam-1' }] })

    const wrapper = mount(CorrectorDashboard, {
      global: {
        components: { AppIcon },
        stubs: ['RouterLink', 'RouterView']
      }
    })

    // Wait for initial load
    await new Promise(resolve => setTimeout(resolve, 100))

    // Trigger stats display
    const btnStats = wrapper.find('.btn-stats')
    if (btnStats.exists()) {
        await btnStats.trigger('click')
    } else {
        // Fallback if button not found, try scrolling to stats
        const navStats = wrapper.find('.btn-nav-stats')
        if (navStats.exists()) await navStats.trigger('click')
    }
    
    // Wait for stats fetch
    await new Promise(resolve => setTimeout(resolve, 100))

    const csvButtons = wrapper.findAll('.btn-export-table')
    expect(csvButtons.length).toBeGreaterThan(0)
    expect(csvButtons[0].text()).toContain('CSV')
  })
})
