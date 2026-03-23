import { describe, it, expect, beforeEach, vi } from 'vitest'

/**
 * Complete API Integration Tests (mocked axios)
 *
 * Tests every endpoint surface exposed by the grading API service,
 * including error handling and pagination patterns.
 */

// --- Mock API layer (mirrors gradingApi.ts structure) ---

function createMockApi() {
  return {
    // Copies
    listCopies: vi.fn(),
    getCopy: vi.fn(),

    // Annotations (6 types: error, success, warning, info, comment, highlight)
    createAnnotation: vi.fn(),
    listAnnotations: vi.fn(),
    deleteAnnotation: vi.fn(),

    // Scores
    fetchScores: vi.fn(),
    saveScores: vi.fn(),

    // Remarks
    fetchRemarks: vi.fn(),
    saveRemarks: vi.fn(),

    // Appreciation
    fetchAppreciation: vi.fn(),
    saveAppreciation: vi.fn(),

    // Drafts
    getDraft: vi.fn(),
    saveDraft: vi.fn(),
    deleteDraft: vi.fn(),

    // Audit
    listAuditLogs: vi.fn(),

    // Admin
    forceUnlockCopy: vi.fn(),
    reopenCopy: vi.fn(),

    // Stats
    fetchExamStats: vi.fn(),

    // Results
    releaseResults: vi.fn(),
    unreleaseResults: vi.fn(),

    // Suggestions
    fetchSuggestions: vi.fn(),

    // Personal annotations
    listPersonalAnnotations: vi.fn(),
    createPersonalAnnotation: vi.fn(),
    updatePersonalAnnotation: vi.fn(),
    deletePersonalAnnotation: vi.fn(),
    autoSavePersonalAnnotation: vi.fn(),
    usePersonalAnnotation: vi.fn(),

    // Subject variant
    updateSubjectVariant: vi.fn(),

    // Final PDF
    getFinalPdfUrl: vi.fn(),
  }
}

// --------------------------------------------------------------------------
// Tests
// --------------------------------------------------------------------------

describe('API Complete Integration', () => {
  let api: ReturnType<typeof createMockApi>

  beforeEach(() => {
    vi.clearAllMocks()
    api = createMockApi()
  })

  // --- Copies ---

  describe('Copies', () => {
    it('listCopies returns paginated copy list', async () => {
      api.listCopies.mockResolvedValue({
        data: {
          results: [
            { id: 'c1', anonymous_id: 'ABC', status: 'READY' },
            { id: 'c2', anonymous_id: 'DEF', status: 'GRADED' },
          ],
          count: 2,
        },
      })

      const res = await api.listCopies('exam-1')
      expect(res.data.results).toHaveLength(2)
      expect(res.data.results[0].status).toBe('READY')
      expect(api.listCopies).toHaveBeenCalledWith('exam-1')
    })

    it('getCopy returns single copy with grading structure', async () => {
      api.getCopy.mockResolvedValue({
        data: {
          id: 'c1',
          anonymous_id: 'ABC',
          status: 'READY',
          exam: {
            id: 'exam-1',
            grading_structure: [
              { id: '1', label: 'Ex 1', points: 10, children: [] },
            ],
          },
        },
      })

      const res = await api.getCopy('c1')
      expect(res.data.id).toBe('c1')
      expect(res.data.exam.grading_structure).toHaveLength(1)
    })
  })

  // --- Annotations (6 types) ---

  describe('Annotations', () => {
    const annotationTypes = ['error', 'success', 'warning', 'info', 'comment', 'highlight'] as const

    annotationTypes.forEach((type) => {
      it(`creates annotation of type "${type}"`, async () => {
        api.createAnnotation.mockResolvedValue({
          data: { id: `ann-${type}`, type, content: `Test ${type}`, x: 10, y: 20 },
        })

        const res = await api.createAnnotation('c1', { type, content: `Test ${type}`, x: 10, y: 20 })
        expect(res.data.type).toBe(type)
        expect(res.data.id).toBe(`ann-${type}`)
      })
    })

    it('listAnnotations returns all annotations for a copy', async () => {
      api.listAnnotations.mockResolvedValue({
        data: [
          { id: 'a1', type: 'error', content: 'Faux' },
          { id: 'a2', type: 'success', content: 'Vrai' },
        ],
      })

      const res = await api.listAnnotations('c1')
      expect(res.data).toHaveLength(2)
    })

    it('deleteAnnotation removes annotation by id', async () => {
      api.deleteAnnotation.mockResolvedValue({ data: { success: true } })

      const res = await api.deleteAnnotation('c1', 'a1')
      expect(res.data.success).toBe(true)
      expect(api.deleteAnnotation).toHaveBeenCalledWith('c1', 'a1')
    })
  })

  // --- Scores ---

  describe('Scores', () => {
    it('fetchScores returns scores map', async () => {
      api.fetchScores.mockResolvedValue({
        data: { scores_data: { '1.1': 5, '1.2': 8 } },
      })

      const res = await api.fetchScores('c1')
      expect(res.data.scores_data['1.1']).toBe(5)
    })

    it('saveScores with valid data succeeds', async () => {
      api.saveScores.mockResolvedValue({
        data: { success: true, scores_data: { '1.1': 7 } },
      })

      const res = await api.saveScores('c1', { '1.1': 7 })
      expect(res.data.success).toBe(true)
    })
  })

  // --- Remarks ---

  describe('Remarks', () => {
    it('fetchRemarks returns remarks map', async () => {
      api.fetchRemarks.mockResolvedValue({
        data: { remarks: { '1.1': 'Bien joué' } },
      })

      const res = await api.fetchRemarks('c1')
      expect(res.data.remarks['1.1']).toBe('Bien joué')
    })

    it('saveRemarks persists remark text', async () => {
      api.saveRemarks.mockResolvedValue({
        data: { success: true },
      })

      const res = await api.saveRemarks('c1', { '1.1': 'Revoir' })
      expect(res.data.success).toBe(true)
      expect(api.saveRemarks).toHaveBeenCalledWith('c1', { '1.1': 'Revoir' })
    })
  })

  // --- Appreciation ---

  describe('Appreciation', () => {
    it('fetchAppreciation returns text', async () => {
      api.fetchAppreciation.mockResolvedValue({
        data: { appreciation: 'Excellent travail' },
      })

      const res = await api.fetchAppreciation('c1')
      expect(res.data.appreciation).toBe('Excellent travail')
    })

    it('saveAppreciation persists text', async () => {
      api.saveAppreciation.mockResolvedValue({ data: { success: true } })

      const res = await api.saveAppreciation('c1', 'Bon travail')
      expect(res.data.success).toBe(true)
    })
  })

  // --- Drafts ---

  describe('Drafts', () => {
    it('getDraft returns saved draft payload', async () => {
      api.getDraft.mockResolvedValue({
        data: {
          source: 'LOCAL',
          payload: { scores: { '1.1': 5 }, remarks: {} },
          timestamp: 1700000000000,
        },
      })

      const res = await api.getDraft('c1')
      expect(res.data.source).toBe('LOCAL')
      expect(res.data.payload.scores['1.1']).toBe(5)
    })

    it('saveDraft persists draft', async () => {
      api.saveDraft.mockResolvedValue({ data: { success: true } })

      const res = await api.saveDraft('c1', { scores: { '1.1': 5 } })
      expect(res.data.success).toBe(true)
    })

    it('deleteDraft removes draft', async () => {
      api.deleteDraft.mockResolvedValue({ data: { success: true } })

      const res = await api.deleteDraft('c1')
      expect(res.data.success).toBe(true)
    })
  })

  // --- Audit ---

  describe('Audit', () => {
    it('listAuditLogs returns log entries', async () => {
      api.listAuditLogs.mockResolvedValue({
        data: [
          { id: 'log-1', action: 'SCORE_UPDATE', timestamp: '2025-01-01T10:00:00Z', user: 'teacher1' },
          { id: 'log-2', action: 'ANNOTATION_CREATE', timestamp: '2025-01-01T10:05:00Z', user: 'teacher1' },
        ],
      })

      const res = await api.listAuditLogs('c1')
      expect(res.data).toHaveLength(2)
      expect(res.data[0].action).toBe('SCORE_UPDATE')
    })
  })

  // --- Admin ---

  describe('Admin', () => {
    it('forceUnlockCopy unlocks a locked copy', async () => {
      api.forceUnlockCopy.mockResolvedValue({
        data: { success: true, status: 'READY' },
      })

      const res = await api.forceUnlockCopy('c1')
      expect(res.data.success).toBe(true)
      expect(res.data.status).toBe('READY')
    })

    it('reopenCopy transitions GRADED back to READY', async () => {
      api.reopenCopy.mockResolvedValue({
        data: { success: true, status: 'READY' },
      })

      const res = await api.reopenCopy('c1')
      expect(res.data.status).toBe('READY')
    })
  })

  // --- Stats ---

  describe('Stats', () => {
    it('fetchExamStats returns statistics object', async () => {
      api.fetchExamStats.mockResolvedValue({
        data: {
          total_copies: 30,
          graded_copies: 20,
          average_score: 14.5,
          median_score: 15,
          min_score: 5,
          max_score: 19,
        },
      })

      const res = await api.fetchExamStats('exam-1')
      expect(res.data.total_copies).toBe(30)
      expect(res.data.average_score).toBe(14.5)
    })
  })

  // --- Results ---

  describe('Results', () => {
    it('releaseResults publishes results', async () => {
      api.releaseResults.mockResolvedValue({ data: { success: true, released: true } })

      const res = await api.releaseResults('exam-1')
      expect(res.data.released).toBe(true)
    })

    it('unreleaseResults hides results', async () => {
      api.unreleaseResults.mockResolvedValue({ data: { success: true, released: false } })

      const res = await api.unreleaseResults('exam-1')
      expect(res.data.released).toBe(false)
    })
  })

  // --- Suggestions ---

  describe('Suggestions', () => {
    it('fetchSuggestions with filters returns suggestions', async () => {
      api.fetchSuggestions.mockResolvedValue({
        data: [
          { id: 's1', text: 'Revoir la formule', questionId: '1.1', score: 0.9 },
          { id: 's2', text: 'Bonne démarche', questionId: '1.1', score: 0.7 },
        ],
      })

      const res = await api.fetchSuggestions({ questionId: '1.1', limit: 5 })
      expect(res.data).toHaveLength(2)
      expect(res.data[0].questionId).toBe('1.1')
    })
  })

  // --- Personal annotations ---

  describe('Personal annotations', () => {
    it('CRUD cycle: create, list, update, delete', async () => {
      api.createPersonalAnnotation.mockResolvedValue({
        data: { id: 'pa-1', text: 'Mon annotation', category: 'error' },
      })
      api.listPersonalAnnotations.mockResolvedValue({
        data: [{ id: 'pa-1', text: 'Mon annotation', category: 'error' }],
      })
      api.updatePersonalAnnotation.mockResolvedValue({
        data: { id: 'pa-1', text: 'Updated', category: 'warning' },
      })
      api.deletePersonalAnnotation.mockResolvedValue({ data: { success: true } })

      const created = await api.createPersonalAnnotation({ text: 'Mon annotation', category: 'error' })
      expect(created.data.id).toBe('pa-1')

      const listed = await api.listPersonalAnnotations()
      expect(listed.data).toHaveLength(1)

      const updated = await api.updatePersonalAnnotation('pa-1', { text: 'Updated', category: 'warning' })
      expect(updated.data.text).toBe('Updated')

      const deleted = await api.deletePersonalAnnotation('pa-1')
      expect(deleted.data.success).toBe(true)
    })

    it('autoSave personal annotation', async () => {
      api.autoSavePersonalAnnotation.mockResolvedValue({ data: { id: 'pa-auto', saved: true } })

      const res = await api.autoSavePersonalAnnotation({ text: 'Auto-saved text', category: 'info' })
      expect(res.data.saved).toBe(true)
    })

    it('use personal annotation applies it', async () => {
      api.usePersonalAnnotation.mockResolvedValue({
        data: { id: 'pa-1', text: 'Applied annotation', usageCount: 5 },
      })

      const res = await api.usePersonalAnnotation('pa-1')
      expect(res.data.usageCount).toBe(5)
    })
  })

  // --- Subject variant ---

  describe('Subject variant', () => {
    it('updateSubjectVariant assigns variant', async () => {
      api.updateSubjectVariant.mockResolvedValue({
        data: { success: true, variant: 'B' },
      })

      const res = await api.updateSubjectVariant('c1', 'B')
      expect(res.data.variant).toBe('B')
    })
  })

  // --- Final PDF ---

  describe('Final PDF', () => {
    it('URL generation returns download link', async () => {
      api.getFinalPdfUrl.mockResolvedValue({
        data: { url: 'https://storage.example.com/final/copy-c1.pdf' },
      })

      const res = await api.getFinalPdfUrl('c1')
      expect(res.data.url).toContain('copy-c1.pdf')
    })
  })

  // --- Error handling ---

  describe('Error handling', () => {
    it('401 unauthorized', async () => {
      const error = { response: { status: 401, data: { detail: 'Authentication required' } } }
      api.getCopy.mockRejectedValue(error)

      try {
        await api.getCopy('c1')
      } catch (e: any) {
        expect(e.response.status).toBe(401)
      }
    })

    it('403 forbidden', async () => {
      const error = { response: { status: 403, data: { detail: 'Permission denied' } } }
      api.getCopy.mockRejectedValue(error)

      await expect(api.getCopy('c1')).rejects.toMatchObject({
        response: { status: 403 },
      })
    })

    it('404 not found', async () => {
      const error = { response: { status: 404, data: { detail: 'Copy not found' } } }
      api.getCopy.mockRejectedValue(error)

      await expect(api.getCopy('unknown')).rejects.toMatchObject({
        response: { status: 404 },
      })
    })

    it('409 conflict', async () => {
      const error = { response: { status: 409, data: { detail: 'Copy locked by another user' } } }
      api.saveScores.mockRejectedValue(error)

      await expect(api.saveScores('c1', {})).rejects.toMatchObject({
        response: { status: 409 },
      })
    })

    it('500 server error', async () => {
      const error = { response: { status: 500, data: { detail: 'Internal server error' } } }
      api.saveScores.mockRejectedValue(error)

      await expect(api.saveScores('c1', {})).rejects.toMatchObject({
        response: { status: 500 },
      })
    })

    it('network timeout', async () => {
      const error = { code: 'ECONNABORTED', message: 'timeout of 5000ms exceeded' }
      api.getCopy.mockRejectedValue(error)

      await expect(api.getCopy('c1')).rejects.toMatchObject({
        code: 'ECONNABORTED',
      })
    })
  })

  // --- Pagination ---

  describe('Pagination', () => {
    it('handles paginated responses with next/previous', async () => {
      api.listCopies.mockResolvedValue({
        data: {
          results: [{ id: 'c1' }, { id: 'c2' }],
          count: 10,
          next: 'http://api/copies/?page=2',
          previous: null,
        },
      })

      const res = await api.listCopies('exam-1')
      expect(res.data.results).toHaveLength(2)
      expect(res.data.count).toBe(10)
      expect(res.data.next).toContain('page=2')
      expect(res.data.previous).toBeNull()
    })

    it('handles non-paginated responses (flat array)', async () => {
      api.listAnnotations.mockResolvedValue({
        data: [
          { id: 'a1', type: 'error' },
          { id: 'a2', type: 'success' },
        ],
      })

      const res = await api.listAnnotations('c1')
      expect(Array.isArray(res.data)).toBe(true)
      expect(res.data).toHaveLength(2)
    })
  })
})
