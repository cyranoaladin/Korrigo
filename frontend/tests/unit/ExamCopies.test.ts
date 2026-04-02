import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

import ExamCopies from '../../src/views/admin/ExamCopies.vue'

const { mockPush, mockApiGet } = vi.hoisted(() => ({
  mockPush: vi.fn(),
  mockApiGet: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { examId: 'exam-123' } }),
  useRouter: () => ({ push: mockPush }),
}))

vi.mock('../../src/services/api', () => ({
  default: { get: mockApiGet },
}))

describe('ExamCopies', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('exports annotations as JSON', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url === '/exams/exam-123/copies/') {
        return Promise.resolve({ data: { results: [], count: 0 } })
      }
      if (url === '/grading/exams/exam-123/export-all-annotations/') {
        return Promise.resolve({ data: { exam_id: 'exam-123', copies: [] } })
      }
      return Promise.reject(new Error(`Unexpected URL ${url}`))
    })

    const createObjectURL = vi.fn(() => 'blob:export')
    const revokeObjectURL = vi.fn()
    global.URL.createObjectURL = createObjectURL
    global.URL.revokeObjectURL = revokeObjectURL

    const click = vi.fn()
    const originalCreateElement = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      const element = originalCreateElement(tagName)
      if (tagName === 'a') {
        element.click = click
      }
      return element
    })

    const wrapper = mount(ExamCopies, {
      global: {
        stubs: { ExamUploadModal: true },
      },
    })
    await flushPromises()

    const exportButton = wrapper.findAll('button').find((button) => button.text().includes('Exporter annotations JSON'))
    expect(exportButton).toBeTruthy()
    await exportButton.trigger('click')
    await flushPromises()

    expect(mockApiGet).toHaveBeenCalledWith('/grading/exams/exam-123/export-all-annotations/', { params: { format: 'json' } })
    expect(createObjectURL).toHaveBeenCalled()
    expect(click).toHaveBeenCalled()
  })
})
