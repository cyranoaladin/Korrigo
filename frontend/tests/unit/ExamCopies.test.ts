import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

import ExamCopies from '../../src/views/admin/ExamCopies.vue'

const { mockPush, mockApiGet, mockApiPost } = vi.hoisted(() => ({
  mockPush: vi.fn(),
  mockApiGet: vi.fn(),
  mockApiPost: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { examId: 'exam-123' } }),
  useRouter: () => ({ push: mockPush }),
}))

vi.mock('../../src/services/api', () => ({
  default: { get: mockApiGet, post: mockApiPost },
}))

describe('ExamCopies', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('exports annotations as JSON', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url === '/exams/exam-123/student-list/') {
        return Promise.resolve({ data: { summary: { total_students: 0 }, copies: [] } })
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

  it('rotates last pages in batch from the admin modal', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url === '/exams/exam-123/student-list/') {
        return Promise.resolve({ data: { summary: { total_students: 1 }, copies: [] } })
      }
      return Promise.reject(new Error(`Unexpected URL ${url}`))
    })
    mockApiPost.mockImplementation((url: string, body: any) => {
      if (url === '/exams/exam-123/copies/rotate-last-pages/') {
        expect(body).toEqual({ anonymous_ids: ['69CB-010', '69CB-074', '69CB-094'] })
        return Promise.resolve({
          data: {
            rotated_count: 3,
            error_count: 0,
            rotated: [],
            errors: [],
          },
        })
      }
      return Promise.reject(new Error(`Unexpected URL ${url}`))
    })

    const wrapper = mount(ExamCopies, {
      global: {
        stubs: { ExamUploadModal: true },
      },
    })
    await flushPromises()

    const rotateButton = wrapper.findAll('button').find((button) => button.text().includes('Rotation dernière page'))
    expect(rotateButton).toBeTruthy()
    await rotateButton.trigger('click')
    await flushPromises()

    const textarea = wrapper.find('textarea')
    await textarea.setValue('69CB-010, 69CB-074\n69CB-094')
    await flushPromises()

    const submitButton = wrapper.findAll('button').find((button) => button.text().includes('Lancer la rotation'))
    expect(submitButton).toBeTruthy()
    await submitButton.trigger('click')
    await flushPromises()

    expect(mockApiPost).toHaveBeenCalledWith('/exams/exam-123/copies/rotate-last-pages/', {
      anonymous_ids: ['69CB-010', '69CB-074', '69CB-094'],
    })
  })
})
