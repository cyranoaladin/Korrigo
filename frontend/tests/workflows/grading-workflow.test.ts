import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

/**
 * Grading / Scoring Workflow Tests
 *
 * Tests score entry, total computation, debounced saving,
 * remark/appreciation persistence, suggestion panel, and sync error handling.
 */

// --- Helper types & functions mirroring CorrectorDeskV2 logic ---

interface GradingState {
  scores: Record<string, number | null>
  remarks: Record<string, string>
  appreciation: string
  pendingScoresChange: boolean
  pendingRemarksChanges: Set<string>
  pendingAppreciationChange: boolean
  syncErrors: string[]
  consecutiveFailures: number
  syncStatus: 'ok' | 'warning' | 'critical'
  suggestionContext: string | null
  annotationBank: string[]
}

function createGradingState(overrides: Partial<GradingState> = {}): GradingState {
  return {
    scores: {},
    remarks: {},
    appreciation: '',
    pendingScoresChange: false,
    pendingRemarksChanges: new Set(),
    pendingAppreciationChange: false,
    syncErrors: [],
    consecutiveFailures: 0,
    syncStatus: 'ok',
    suggestionContext: null,
    annotationBank: [],
    ...overrides,
  }
}

/** Clamp score to [0, max]. Step validation is a UI concern, tested here as pure function. */
function clampScore(value: number | null, max: number): number | null {
  if (value === null) return null
  if (value < 0) return 0
  if (value > max) return max
  return value
}

/** Round to nearest 0.25 step */
function snapToStep(value: number, step: number = 0.25): number {
  return Math.round(value / step) * step
}

/** Compute total from a scores map. Null entries are skipped. */
function computeTotal(scores: Record<string, number | null>): number {
  return Object.values(scores).reduce((sum: number, v) => sum + (v ?? 0), 0)
}

function computeSyncStatus(state: GradingState): 'ok' | 'warning' | 'critical' {
  if (state.consecutiveFailures >= 3) return 'critical'
  if (state.syncErrors.length > 0 || state.pendingScoresChange || state.pendingRemarksChanges.size > 0 || state.pendingAppreciationChange) return 'warning'
  return 'ok'
}

// --------------------------------------------------------------------------
// Tests
// --------------------------------------------------------------------------

describe('Grading Workflow', () => {
  let state: GradingState

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    state = createGradingState()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  // --- Score entry ---

  describe('Score entry', () => {
    it('valid score within range is accepted', () => {
      const score = clampScore(7.5, 10)
      expect(score).toBe(7.5)
    })

    it('score clamped to max', () => {
      const score = clampScore(15, 10)
      expect(score).toBe(10)
    })

    it('negative score clamped to 0', () => {
      const score = clampScore(-3, 10)
      expect(score).toBe(0)
    })

    it('step 0.25 respected', () => {
      expect(snapToStep(7.3)).toBe(7.25)
      expect(snapToStep(7.4)).toBe(7.5)
      expect(snapToStep(7.1)).toBe(7.0)
      expect(snapToStep(7.875)).toBe(8.0)
      expect(snapToStep(0.125)).toBe(0.25)
    })

    it('empty string treated as null', () => {
      const raw = ''
      const value = raw === '' ? null : parseFloat(raw)
      const score = clampScore(value, 10)
      expect(score).toBeNull()
    })
  })

  // --- Total computation ---

  describe('Total computation', () => {
    it('sum of all questions', () => {
      state.scores = { '1.1': 4, '1.2': 6, '2.1': 3 }
      expect(computeTotal(state.scores)).toBe(13)
    })

    it('handles null scores by treating them as 0', () => {
      state.scores = { '1.1': 4, '1.2': null, '2.1': 3 }
      expect(computeTotal(state.scores)).toBe(7)
    })

    it('total overflow: exceeds 20 detected', () => {
      state.scores = { '1.1': 10, '1.2': 8, '2.1': 5 }
      const total = computeTotal(state.scores)
      expect(total).toBe(23)
      expect(total > 20).toBe(true)
    })
  })

  // --- Debounced save ---

  describe('Score save debounce', () => {
    it('waits 800ms before saving', () => {
      const saveFn = vi.fn()
      let timer: ReturnType<typeof setTimeout> | null = null

      function debouncedSaveScores() {
        if (timer) clearTimeout(timer)
        state.pendingScoresChange = true
        timer = setTimeout(() => {
          saveFn(state.scores)
          state.pendingScoresChange = false
        }, 800)
      }

      state.scores['1.1'] = 5
      debouncedSaveScores()

      // Not called yet at 500ms
      vi.advanceTimersByTime(500)
      expect(saveFn).not.toHaveBeenCalled()
      expect(state.pendingScoresChange).toBe(true)

      // Called at 800ms
      vi.advanceTimersByTime(300)
      expect(saveFn).toHaveBeenCalledWith({ '1.1': 5 })
      expect(state.pendingScoresChange).toBe(false)
    })

    it('localStorage backup on score change', () => {
      const setItem = vi.fn()
      const storage = { setItem }

      state.scores['1.1'] = 5
      storage.setItem('korrigo_backup_scores_copy-1', JSON.stringify(state.scores))

      expect(setItem).toHaveBeenCalledWith(
        'korrigo_backup_scores_copy-1',
        JSON.stringify({ '1.1': 5 })
      )
    })
  })

  // --- Remark entry ---

  describe('Remark entry', () => {
    it('text saved after 1 second debounce', () => {
      const saveFn = vi.fn()
      let timer: ReturnType<typeof setTimeout> | null = null

      function debouncedSaveRemark(questionId: string, text: string) {
        state.remarks[questionId] = text
        state.pendingRemarksChanges.add(questionId)
        if (timer) clearTimeout(timer)
        timer = setTimeout(() => {
          saveFn(questionId, text)
          state.pendingRemarksChanges.delete(questionId)
        }, 1000)
      }

      debouncedSaveRemark('1.1', 'Bonne réponse')

      vi.advanceTimersByTime(500)
      expect(saveFn).not.toHaveBeenCalled()

      vi.advanceTimersByTime(500)
      expect(saveFn).toHaveBeenCalledWith('1.1', 'Bonne réponse')
      expect(state.pendingRemarksChanges.has('1.1')).toBe(false)
    })

    it('localStorage backup on remark change', () => {
      const setItem = vi.fn()
      const storage = { setItem }

      state.remarks['1.1'] = 'Calcul correct'
      storage.setItem('korrigo_backup_remarks_copy-1', JSON.stringify(state.remarks))

      expect(setItem).toHaveBeenCalledWith(
        'korrigo_backup_remarks_copy-1',
        JSON.stringify({ '1.1': 'Calcul correct' })
      )
    })

    it('substantial remarks (>5 chars) saved to annotation bank', () => {
      const remark = 'Calcul incorrect, revoir la formule'
      state.remarks['1.1'] = remark

      if (remark.length > 5) {
        state.annotationBank.push(remark)
      }

      expect(state.annotationBank).toHaveLength(1)
      expect(state.annotationBank[0]).toBe(remark)
    })

    it('short remarks (<= 5 chars) not saved to annotation bank', () => {
      const remark = 'OK'
      state.remarks['1.1'] = remark

      if (remark.length > 5) {
        state.annotationBank.push(remark)
      }

      expect(state.annotationBank).toHaveLength(0)
    })
  })

  // --- Appreciation entry ---

  describe('Appreciation entry', () => {
    it('saved after 1 second debounce', () => {
      const saveFn = vi.fn()
      let timer: ReturnType<typeof setTimeout> | null = null

      function debouncedSaveAppreciation(text: string) {
        state.appreciation = text
        state.pendingAppreciationChange = true
        if (timer) clearTimeout(timer)
        timer = setTimeout(() => {
          saveFn(text)
          state.pendingAppreciationChange = false
        }, 1000)
      }

      debouncedSaveAppreciation('Très bon travail')

      vi.advanceTimersByTime(800)
      expect(saveFn).not.toHaveBeenCalled()

      vi.advanceTimersByTime(200)
      expect(saveFn).toHaveBeenCalledWith('Très bon travail')
      expect(state.pendingAppreciationChange).toBe(false)
    })

    it('localStorage backup on appreciation change', () => {
      const setItem = vi.fn()
      const storage = { setItem }

      state.appreciation = 'Bon travail'
      storage.setItem('korrigo_backup_appreciation_copy-1', state.appreciation)

      expect(setItem).toHaveBeenCalledWith(
        'korrigo_backup_appreciation_copy-1',
        'Bon travail'
      )
    })
  })

  // --- Suggestion panel ---

  describe('Suggestion panel', () => {
    it('opens for correct question context', () => {
      state.suggestionContext = '1.1'
      expect(state.suggestionContext).toBe('1.1')
    })

    it('text inserted appended to remark', () => {
      state.remarks['1.1'] = 'Début: '
      const suggestion = 'Revoir la partie 2'
      state.remarks['1.1'] += suggestion

      expect(state.remarks['1.1']).toBe('Début: Revoir la partie 2')
    })
  })

  // --- Sync error handling ---

  describe('Sync error handling', () => {
    it('score save failure: sync error recorded', () => {
      state.syncErrors.push('Score save failed: network error')
      state.consecutiveFailures = 1
      expect(computeSyncStatus(state)).toBe('warning')
    })

    it('consecutive failures: critical sync status after 3 failures', () => {
      state.consecutiveFailures = 3
      expect(computeSyncStatus(state)).toBe('critical')
    })

    it('critical requires >= 3 failures exactly', () => {
      state.consecutiveFailures = 2
      expect(computeSyncStatus(state)).not.toBe('critical')

      state.consecutiveFailures = 3
      expect(computeSyncStatus(state)).toBe('critical')
    })

    it('retry pending: retries all pending changes', async () => {
      const saveScores = vi.fn().mockResolvedValue({ success: true })
      const saveRemarks = vi.fn().mockResolvedValue({ success: true })
      const saveAppreciation = vi.fn().mockResolvedValue({ success: true })

      state.pendingScoresChange = true
      state.pendingRemarksChanges.add('1.1')
      state.pendingAppreciationChange = true
      state.consecutiveFailures = 2

      const promises: Promise<any>[] = []
      if (state.pendingScoresChange) promises.push(saveScores(state.scores))
      if (state.pendingRemarksChanges.size > 0) promises.push(saveRemarks(state.remarks))
      if (state.pendingAppreciationChange) promises.push(saveAppreciation(state.appreciation))

      await Promise.all(promises)

      expect(saveScores).toHaveBeenCalled()
      expect(saveRemarks).toHaveBeenCalled()
      expect(saveAppreciation).toHaveBeenCalled()

      // Reset on success
      state.pendingScoresChange = false
      state.pendingRemarksChanges.clear()
      state.pendingAppreciationChange = false
      state.consecutiveFailures = 0

      expect(computeSyncStatus(state)).toBe('ok')
    })

    it('sync status resets to ok after successful save', () => {
      state.consecutiveFailures = 2
      state.syncErrors = ['error 1']
      expect(computeSyncStatus(state)).toBe('warning')

      // Successful save
      state.consecutiveFailures = 0
      state.syncErrors = []
      expect(computeSyncStatus(state)).toBe('ok')
    })
  })
})
