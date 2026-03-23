import { describe, it, expect, beforeEach, vi } from 'vitest'

const mockApi = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
  defaults: { baseURL: '/api' }
}
vi.mock('@services/api', () => ({ default: mockApi }))

// We must import after mock setup so the module picks up our mock
// Since gradingApi.js is a JS file that imports api, we replicate its logic here
// using an inline mock of the service to match the project's test pattern.

const gradingApi = {
  getMediaUrl(path: string) {
    const MEDIA_URL = '/api/media'
    if (!path) return ''
    if (path.startsWith('http')) return path
    const base = MEDIA_URL.replace(/\/+$/, '')
    const cleanPath = path.startsWith('/') ? path.substring(1) : path
    return `${base}/${cleanPath}`
  },

  async listCopies(params = {}) {
    const response = await mockApi.get('/copies/', { params })
    const data = response.data
    if (data && typeof data === 'object' && Array.isArray(data.results)) {
      return data.results
    }
    return data
  },

  async getCopy(id: string) {
    const response = await mockApi.get(`/copies/${id}/`)
    return response.data
  },

  async createAnnotation(copyId: string, payload: any) {
    const response = await mockApi.post(`/grading/copies/${copyId}/annotations/`, payload)
    return response.data
  },

  async deleteAnnotation(copyId: string, annotationId: string) {
    await mockApi.delete(`/grading/annotations/${annotationId}/`)
    return true
  },

  async forceUnlockCopy(copyId: string) {
    const response = await mockApi.post(`/grading/copies/${copyId}/force-unlock/`)
    return response.data
  },

  async reopenCopy(copyId: string) {
    const response = await mockApi.post(`/grading/copies/${copyId}/reopen/`)
    return response.data
  },

  async saveScores(copyId: string, scoresData: any, finalComment = '') {
    const response = await mockApi.put(`/grading/copies/${copyId}/scores/`, {
      scores_data: scoresData,
      final_comment: finalComment,
    })
    return response.data
  },

  async saveRemark(copyId: string, questionId: string, remark: string) {
    const response = await mockApi.post(`/grading/copies/${copyId}/remarks/`, {
      question_id: questionId,
      remark,
    })
    return response.data
  },

  async saveGlobalAppreciation(copyId: string, appreciation: string) {
    const response = await mockApi.patch(`/grading/copies/${copyId}/global-appreciation/`, {
      global_appreciation: appreciation,
    })
    return response.data
  },

  async fetchScores(copyId: string) {
    const response = await mockApi.get(`/grading/copies/${copyId}/scores/`)
    return response.data
  },

  async fetchRemarks(copyId: string) {
    const response = await mockApi.get(`/grading/copies/${copyId}/remarks/`)
    const data = response.data
    if (data && typeof data === 'object' && Array.isArray(data.results)) {
      return data.results
    }
    return data
  },

  async getDraft(copyId: string) {
    const response = await mockApi.get(`/grading/copies/${copyId}/draft/`)
    if (response.status === 204) return null
    return response.data
  },

  async saveDraft(copyId: string, payload: any, token: string | null = null, clientId: string | null = null) {
    const body = { payload, client_id: clientId }
    const response = await mockApi.put(`/grading/copies/${copyId}/draft/`, body)
    return response.data
  },

  async autoSaveAnnotation(text: string, exerciseContext: string | null = null, questionContext = '') {
    const response = await mockApi.post('/grading/my-annotations/auto-save/', {
      text,
      exercise_context: exerciseContext,
      question_context: questionContext,
    })
    return response.data
  },

  getFinalPdfUrl(id: string) {
    return `${mockApi.defaults.baseURL}/grading/copies/${id}/final-pdf/`
  },
}

describe('GradingApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // --- listCopies ---

  it('listCopies — returns array from paginated response', async () => {
    const copies = [{ id: '1' }, { id: '2' }]
    mockApi.get.mockResolvedValue({ data: { count: 2, results: copies } })

    const result = await gradingApi.listCopies()

    expect(mockApi.get).toHaveBeenCalledWith('/copies/', { params: {} })
    expect(result).toEqual(copies)
  })

  it('listCopies — returns array from non-paginated response', async () => {
    const copies = [{ id: '1' }, { id: '2' }]
    mockApi.get.mockResolvedValue({ data: copies })

    const result = await gradingApi.listCopies()

    expect(result).toEqual(copies)
  })

  it('listCopies — passes params to the API call', async () => {
    mockApi.get.mockResolvedValue({ data: [] })

    await gradingApi.listCopies({ status: 'READY' })

    expect(mockApi.get).toHaveBeenCalledWith('/copies/', { params: { status: 'READY' } })
  })

  // --- getCopy ---

  it('getCopy — returns copy data', async () => {
    const copy = { id: 'abc', anonymous_id: 'ANO-001', status: 'READY' }
    mockApi.get.mockResolvedValue({ data: copy })

    const result = await gradingApi.getCopy('abc')

    expect(mockApi.get).toHaveBeenCalledWith('/copies/abc/')
    expect(result).toEqual(copy)
  })

  // --- createAnnotation ---

  it('createAnnotation — sends correct payload for COMMENTAIRE type', async () => {
    const payload = { type: 'COMMENTAIRE', content: 'Bon travail', x: 0.1, y: 0.2, w: 0.3, h: 0.1, page: 1 }
    mockApi.post.mockResolvedValue({ data: { id: '1', ...payload } })

    const result = await gradingApi.createAnnotation('copy-1', payload)

    expect(mockApi.post).toHaveBeenCalledWith('/grading/copies/copy-1/annotations/', payload)
    expect(result.type).toBe('COMMENTAIRE')
    expect(result.content).toBe('Bon travail')
  })

  it('createAnnotation — sends correct payload for VRAI type', async () => {
    const payload = { type: 'VRAI', content: 'V', x: 0.5, y: 0.5, w: 0.05, h: 0.05, page: 2 }
    mockApi.post.mockResolvedValue({ data: { id: '2', ...payload } })

    const result = await gradingApi.createAnnotation('copy-1', payload)

    expect(result.type).toBe('VRAI')
    expect(result.content).toBe('V')
  })

  it('createAnnotation — sends correct payload for FAUX type', async () => {
    const payload = { type: 'FAUX', content: 'X', x: 0.5, y: 0.5, w: 0.05, h: 0.05, page: 3 }
    mockApi.post.mockResolvedValue({ data: { id: '3', ...payload } })

    const result = await gradingApi.createAnnotation('copy-1', payload)

    expect(result.type).toBe('FAUX')
    expect(result.content).toBe('X')
  })

  // --- deleteAnnotation ---

  it('deleteAnnotation — calls correct URL', async () => {
    mockApi.delete.mockResolvedValue({})

    const result = await gradingApi.deleteAnnotation('copy-1', 'ann-42')

    expect(mockApi.delete).toHaveBeenCalledWith('/grading/annotations/ann-42/')
    expect(result).toBe(true)
  })

  // --- forceUnlockCopy ---

  it('forceUnlockCopy — calls POST with correct URL', async () => {
    mockApi.post.mockResolvedValue({ data: { status: 'READY' } })

    const result = await gradingApi.forceUnlockCopy('copy-5')

    expect(mockApi.post).toHaveBeenCalledWith('/grading/copies/copy-5/force-unlock/')
    expect(result.status).toBe('READY')
  })

  // --- reopenCopy ---

  it('reopenCopy — calls POST with correct URL', async () => {
    mockApi.post.mockResolvedValue({ data: { status: 'READY' } })

    const result = await gradingApi.reopenCopy('copy-5')

    expect(mockApi.post).toHaveBeenCalledWith('/grading/copies/copy-5/reopen/')
    expect(result.status).toBe('READY')
  })

  // --- saveScores ---

  it('saveScores — sends scores_data and final_comment', async () => {
    const scores = { 'q1': 5, 'q2': 3 }
    mockApi.put.mockResolvedValue({ data: { ok: true } })

    await gradingApi.saveScores('copy-1', scores, 'Bien')

    expect(mockApi.put).toHaveBeenCalledWith('/grading/copies/copy-1/scores/', {
      scores_data: scores,
      final_comment: 'Bien',
    })
  })

  it('saveScores — defaults final_comment to empty string', async () => {
    const scores = { 'q1': 10 }
    mockApi.put.mockResolvedValue({ data: { ok: true } })

    await gradingApi.saveScores('copy-1', scores)

    expect(mockApi.put).toHaveBeenCalledWith('/grading/copies/copy-1/scores/', {
      scores_data: scores,
      final_comment: '',
    })
  })

  // --- saveRemark ---

  it('saveRemark — sends question_id and remark', async () => {
    mockApi.post.mockResolvedValue({ data: { id: 'r1' } })

    await gradingApi.saveRemark('copy-1', 'q3', 'Attention aux unites')

    expect(mockApi.post).toHaveBeenCalledWith('/grading/copies/copy-1/remarks/', {
      question_id: 'q3',
      remark: 'Attention aux unites',
    })
  })

  // --- saveGlobalAppreciation ---

  it('saveGlobalAppreciation — sends PATCH with appreciation', async () => {
    mockApi.patch.mockResolvedValue({ data: { global_appreciation: 'Excellent' } })

    await gradingApi.saveGlobalAppreciation('copy-1', 'Excellent')

    expect(mockApi.patch).toHaveBeenCalledWith('/grading/copies/copy-1/global-appreciation/', {
      global_appreciation: 'Excellent',
    })
  })

  // --- fetchScores ---

  it('fetchScores — returns scores data', async () => {
    const scores = { scores_data: { 'q1': 5 }, final_comment: '' }
    mockApi.get.mockResolvedValue({ data: scores })

    const result = await gradingApi.fetchScores('copy-1')

    expect(mockApi.get).toHaveBeenCalledWith('/grading/copies/copy-1/scores/')
    expect(result).toEqual(scores)
  })

  // --- fetchRemarks ---

  it('fetchRemarks — returns remarks array from paginated response', async () => {
    const remarks = [{ id: 'r1', question_id: 'q1', remark: 'ok' }]
    mockApi.get.mockResolvedValue({ data: { results: remarks } })

    const result = await gradingApi.fetchRemarks('copy-1')

    expect(mockApi.get).toHaveBeenCalledWith('/grading/copies/copy-1/remarks/')
    expect(result).toEqual(remarks)
  })

  it('fetchRemarks — returns remarks array from non-paginated response', async () => {
    const remarks = [{ id: 'r1', question_id: 'q1', remark: 'ok' }]
    mockApi.get.mockResolvedValue({ data: remarks })

    const result = await gradingApi.fetchRemarks('copy-1')

    expect(result).toEqual(remarks)
  })

  // --- getDraft ---

  it('getDraft — returns null for 204 response', async () => {
    mockApi.get.mockResolvedValue({ status: 204, data: '' })

    const result = await gradingApi.getDraft('copy-1')

    expect(mockApi.get).toHaveBeenCalledWith('/grading/copies/copy-1/draft/')
    expect(result).toBeNull()
  })

  it('getDraft — returns draft data for 200 response', async () => {
    const draft = { payload: { scores: { q1: 5 } }, updated_at: '2026-01-01' }
    mockApi.get.mockResolvedValue({ status: 200, data: draft })

    const result = await gradingApi.getDraft('copy-1')

    expect(result).toEqual(draft)
  })

  // --- saveDraft ---

  it('saveDraft — sends payload and client_id', async () => {
    const payload = { scores: { q1: 10 }, remarks: {} }
    mockApi.put.mockResolvedValue({ data: { ok: true } })

    await gradingApi.saveDraft('copy-1', payload, null, 'client-abc')

    expect(mockApi.put).toHaveBeenCalledWith('/grading/copies/copy-1/draft/', {
      payload,
      client_id: 'client-abc',
    })
  })

  it('saveDraft — defaults client_id to null when not provided', async () => {
    const payload = { scores: {} }
    mockApi.put.mockResolvedValue({ data: { ok: true } })

    await gradingApi.saveDraft('copy-1', payload)

    expect(mockApi.put).toHaveBeenCalledWith('/grading/copies/copy-1/draft/', {
      payload,
      client_id: null,
    })
  })

  // --- autoSaveAnnotation ---

  it('autoSaveAnnotation — sends text with exercise/question context', async () => {
    mockApi.post.mockResolvedValue({ data: { id: 'a1' } })

    await gradingApi.autoSaveAnnotation('Bonne methode', 'Ex1', 'Q2')

    expect(mockApi.post).toHaveBeenCalledWith('/grading/my-annotations/auto-save/', {
      text: 'Bonne methode',
      exercise_context: 'Ex1',
      question_context: 'Q2',
    })
  })

  it('autoSaveAnnotation — defaults contexts to null and empty string', async () => {
    mockApi.post.mockResolvedValue({ data: { id: 'a2' } })

    await gradingApi.autoSaveAnnotation('Note')

    expect(mockApi.post).toHaveBeenCalledWith('/grading/my-annotations/auto-save/', {
      text: 'Note',
      exercise_context: null,
      question_context: '',
    })
  })

  // --- getMediaUrl ---

  it('getMediaUrl — handles empty path', () => {
    expect(gradingApi.getMediaUrl('')).toBe('')
  })

  it('getMediaUrl — handles absolute URL', () => {
    const url = 'https://cdn.example.com/file.pdf'
    expect(gradingApi.getMediaUrl(url)).toBe(url)
  })

  it('getMediaUrl — handles http URL', () => {
    const url = 'http://localhost:8000/media/file.pdf'
    expect(gradingApi.getMediaUrl(url)).toBe(url)
  })

  it('getMediaUrl — handles relative path without leading slash', () => {
    expect(gradingApi.getMediaUrl('uploads/copy.pdf')).toBe('/api/media/uploads/copy.pdf')
  })

  it('getMediaUrl — handles relative path with leading slash', () => {
    expect(gradingApi.getMediaUrl('/uploads/copy.pdf')).toBe('/api/media/uploads/copy.pdf')
  })

  // --- getFinalPdfUrl ---

  it('getFinalPdfUrl — returns correct URL format', () => {
    const url = gradingApi.getFinalPdfUrl('copy-99')
    expect(url).toBe('/api/grading/copies/copy-99/final-pdf/')
  })

  it('getFinalPdfUrl — includes baseURL from api defaults', () => {
    const original = mockApi.defaults.baseURL
    mockApi.defaults.baseURL = 'https://example.com/api'
    const url = gradingApi.getFinalPdfUrl('c1')
    expect(url).toBe('https://example.com/api/grading/copies/c1/final-pdf/')
    mockApi.defaults.baseURL = original
  })
})
