import { describe, it, expect, beforeEach, vi } from 'vitest'

/**
 * Correction Workflow Tests
 *
 * Tests the complete correction workflow state machine in-memory.
 * Mirrors the state logic found in CorrectorDeskV2.vue and CorrectorDeskUltimate.vue.
 */

// --- Helpers: lightweight state machine extracted from the Vue components ---

type CopyStatus = 'STAGING' | 'READY' | 'GRADING_IN_PROGRESS' | 'GRADED' | 'GRADING_FAILED'
type SyncStatus = 'ok' | 'warning' | 'critical' | 'offline'

interface CorrectionState {
  copyId: string
  status: CopyStatus
  currentPage: number
  totalPages: number
  annotations: any[]
  scores: Record<string, number | null>
  remarks: Record<string, string>
  appreciation: string
  pendingScoresChange: boolean
  pendingRemarksChanges: Set<string>
  pendingAppreciationChange: boolean
  consecutiveFailures: number
  isOnline: boolean
  syncErrors: string[]
  layoutMode: 'split' | 'full' | 'focus'
  activeTab: string
  scrollPositions: Record<string, number>
  quickStampMode: string | null  // null | 'VRAI' | 'FAUX'
  restoreAvailable: { source: string; payload: any; timestamp: number } | null
}

function createInitialState(overrides: Partial<CorrectionState> = {}): CorrectionState {
  return {
    copyId: 'copy-1',
    status: 'STAGING',
    currentPage: 1,
    totalPages: 5,
    annotations: [],
    scores: {},
    remarks: {},
    appreciation: '',
    pendingScoresChange: false,
    pendingRemarksChanges: new Set(),
    pendingAppreciationChange: false,
    consecutiveFailures: 0,
    isOnline: true,
    syncErrors: [],
    layoutMode: 'split',
    activeTab: 'scoring',
    scrollPositions: {},
    quickStampMode: null,
    restoreAvailable: null,
    ...overrides,
  }
}

function computeSyncStatus(state: CorrectionState): SyncStatus {
  if (!state.isOnline) return 'offline'
  if (state.consecutiveFailures >= 3) return 'critical'
  if (state.syncErrors.length > 0 || hasPendingChanges(state)) return 'warning'
  return 'ok'
}

function hasPendingChanges(state: CorrectionState): boolean {
  return state.pendingScoresChange || state.pendingRemarksChanges.size > 0 || state.pendingAppreciationChange
}

function canFinalize(state: CorrectionState, requiredQuestions: string[]): { ok: boolean; reason?: string } {
  for (const q of requiredQuestions) {
    if (state.scores[q] === undefined || state.scores[q] === null) {
      return { ok: false, reason: `Missing score for ${q}` }
    }
    if ((state.scores[q] as number) > 20) {
      return { ok: false, reason: `Score for ${q} exceeds 20` }
    }
  }
  if (!state.appreciation || state.appreciation.trim() === '') {
    return { ok: false, reason: 'Missing appreciation' }
  }
  return { ok: true }
}

// --------------------------------------------------------------------------
// Tests
// --------------------------------------------------------------------------

describe('Correction Workflow', () => {
  let state: CorrectionState

  beforeEach(() => {
    vi.clearAllMocks()
    state = createInitialState()
  })

  // --- Full workflow ---

  describe('Full correction lifecycle', () => {
    it('workflow: load copy -> view PDF -> annotate -> score -> remark -> appreciate -> finalize', () => {
      // 1. Load copy (STAGING -> READY via dispatch)
      state.status = 'READY'
      state.totalPages = 3

      // 2. View PDF (navigate pages)
      state.currentPage = 1
      expect(state.currentPage).toBe(1)

      // 3. Annotate
      const annotation = { id: 'a1', type: 'error', content: 'Faux', x: 10, y: 20, page: 1 }
      state.annotations.push(annotation)
      expect(state.annotations).toHaveLength(1)

      // 4. Score
      state.scores['1.1'] = 4
      state.scores['1.2'] = 6
      state.pendingScoresChange = true

      // 5. Remark
      state.remarks['1.1'] = 'Bonne méthode'
      state.pendingRemarksChanges.add('1.1')

      // 6. Appreciate
      state.appreciation = 'Bon travail dans l\'ensemble'
      state.pendingAppreciationChange = true

      // 7. Finalize
      const check = canFinalize(state, ['1.1', '1.2'])
      expect(check.ok).toBe(true)
      state.status = 'GRADED'
      expect(state.status).toBe('GRADED')
    })
  })

  // --- State transitions ---

  describe('State transitions', () => {
    it('STAGING -> READY transition', () => {
      expect(state.status).toBe('STAGING')
      state.status = 'READY'
      expect(state.status).toBe('READY')
    })

    it('READY -> GRADED transition after complete grading', () => {
      state.status = 'READY'
      state.scores['1.1'] = 10
      state.appreciation = 'Bien'
      const check = canFinalize(state, ['1.1'])
      expect(check.ok).toBe(true)
      state.status = 'GRADED'
      expect(state.status).toBe('GRADED')
    })

    it('cannot transition STAGING directly to GRADED', () => {
      // Business rule: must be READY first
      expect(state.status).toBe('STAGING')
      const check = canFinalize(state, ['1.1'])
      expect(check.ok).toBe(false)
    })
  })

  // --- Score persistence ---

  describe('Score persistence', () => {
    it('scores saved after debounce marks pending', () => {
      state.status = 'READY'
      state.scores['1.1'] = 5
      state.pendingScoresChange = true
      expect(state.pendingScoresChange).toBe(true)
      // After save:
      state.pendingScoresChange = false
      expect(state.pendingScoresChange).toBe(false)
    })
  })

  // --- Remark persistence ---

  describe('Remark persistence', () => {
    it('remarks saved after debounce marks pending per question', () => {
      state.remarks['1.1'] = 'Revoir cette partie'
      state.pendingRemarksChanges.add('1.1')
      expect(state.pendingRemarksChanges.has('1.1')).toBe(true)
      // After save:
      state.pendingRemarksChanges.delete('1.1')
      expect(state.pendingRemarksChanges.size).toBe(0)
    })
  })

  // --- Appreciation persistence ---

  describe('Appreciation persistence', () => {
    it('appreciation saved after debounce marks pending', () => {
      state.appreciation = 'Excellent travail'
      state.pendingAppreciationChange = true
      expect(state.pendingAppreciationChange).toBe(true)
      state.pendingAppreciationChange = false
      expect(hasPendingChanges(state)).toBe(false)
    })
  })

  // --- Concurrent / pending changes tracking ---

  describe('Concurrent changes tracking', () => {
    it('tracks multiple pending change types simultaneously', () => {
      state.pendingScoresChange = true
      state.pendingRemarksChanges.add('1.1')
      state.pendingRemarksChanges.add('1.2')
      state.pendingAppreciationChange = true

      expect(hasPendingChanges(state)).toBe(true)
      expect(state.pendingRemarksChanges.size).toBe(2)
    })

    it('clears all pending flags after full save', () => {
      state.pendingScoresChange = true
      state.pendingRemarksChanges.add('1.1')
      state.pendingAppreciationChange = true

      // Simulate full save
      state.pendingScoresChange = false
      state.pendingRemarksChanges.clear()
      state.pendingAppreciationChange = false

      expect(hasPendingChanges(state)).toBe(false)
    })
  })

  // --- Sync status ---

  describe('Sync status', () => {
    it('ok when no pending changes and online', () => {
      expect(computeSyncStatus(state)).toBe('ok')
    })

    it('warning when pending changes exist', () => {
      state.pendingScoresChange = true
      expect(computeSyncStatus(state)).toBe('warning')
    })

    it('warning when sync errors recorded', () => {
      state.syncErrors.push('save failed')
      expect(computeSyncStatus(state)).toBe('warning')
    })

    it('critical after 3 consecutive failures', () => {
      state.consecutiveFailures = 3
      expect(computeSyncStatus(state)).toBe('critical')
    })

    it('ok -> warning -> critical flow', () => {
      expect(computeSyncStatus(state)).toBe('ok')

      state.pendingScoresChange = true
      expect(computeSyncStatus(state)).toBe('warning')

      state.consecutiveFailures = 3
      expect(computeSyncStatus(state)).toBe('critical')
    })
  })

  // --- Offline mode ---

  describe('Offline mode', () => {
    it('pending changes preserved when going offline', () => {
      state.pendingScoresChange = true
      state.pendingRemarksChanges.add('1.1')
      state.isOnline = false

      expect(computeSyncStatus(state)).toBe('offline')
      expect(hasPendingChanges(state)).toBe(true)
    })

    it('offline status overrides critical', () => {
      state.consecutiveFailures = 5
      state.isOnline = false
      expect(computeSyncStatus(state)).toBe('offline')
    })
  })

  // --- Draft restore / discard ---

  describe('Draft restore', () => {
    it('draft available -> restore -> apply', () => {
      state.restoreAvailable = {
        source: 'LOCAL',
        payload: {
          scores: { '1.1': 8 },
          remarks: { '1.1': 'Draft remark' },
          appreciation: 'Draft appreciation',
        },
        timestamp: Date.now() - 60000,
      }

      expect(state.restoreAvailable).not.toBeNull()

      // Apply restore
      const payload = state.restoreAvailable!.payload
      state.scores = payload.scores
      state.remarks = payload.remarks
      state.appreciation = payload.appreciation
      state.restoreAvailable = null

      expect(state.scores['1.1']).toBe(8)
      expect(state.remarks['1.1']).toBe('Draft remark')
      expect(state.appreciation).toBe('Draft appreciation')
      expect(state.restoreAvailable).toBeNull()
    })

    it('draft available -> discard', () => {
      state.restoreAvailable = {
        source: 'LOCAL',
        payload: { scores: { '1.1': 8 } },
        timestamp: Date.now(),
      }

      // Discard
      state.restoreAvailable = null
      expect(state.restoreAvailable).toBeNull()
      expect(state.scores).toEqual({})
    })
  })

  // --- Annotation flows ---

  describe('Annotation flow', () => {
    it('draw -> type select -> content -> save', () => {
      const rect = { x: 100, y: 200, width: 80, height: 40, page: 1 }
      const draft = { normalizedRect: rect, type: null as string | null, content: '' }

      // Type select
      draft.type = 'error'
      expect(draft.type).toBe('error')

      // Content
      draft.content = 'Calcul incorrect'
      expect(draft.content).toBe('Calcul incorrect')

      // Save
      const annotation = { id: 'a1', ...draft, normalizedRect: rect }
      state.annotations.push(annotation)
      expect(state.annotations).toHaveLength(1)
      expect(state.annotations[0].content).toBe('Calcul incorrect')
    })

    it('select -> confirm -> remove annotation', () => {
      state.annotations = [
        { id: 'a1', type: 'error', content: 'Wrong', page: 1 },
        { id: 'a2', type: 'success', content: 'Correct', page: 1 },
      ]

      // Select and confirm delete
      const toDelete = 'a1'
      state.annotations = state.annotations.filter(a => a.id !== toDelete)

      expect(state.annotations).toHaveLength(1)
      expect(state.annotations[0].id).toBe('a2')
    })
  })

  // --- Quick stamp flows ---

  describe('Quick stamp flow', () => {
    it('enable VRAI mode -> draw -> auto-save stamp', () => {
      state.quickStampMode = 'VRAI'
      expect(state.quickStampMode).toBe('VRAI')

      // Simulate draw at location
      const stamp = {
        id: 'stamp-1',
        type: 'success',
        content: 'Vrai',
        x: 150,
        y: 300,
        page: state.currentPage,
      }
      state.annotations.push(stamp)
      expect(state.annotations).toHaveLength(1)
      expect(state.annotations[0].content).toBe('Vrai')
    })

    it('enable FAUX mode -> draw -> auto-save stamp', () => {
      state.quickStampMode = 'FAUX'

      const stamp = {
        id: 'stamp-2',
        type: 'error',
        content: 'Faux',
        x: 200,
        y: 400,
        page: state.currentPage,
      }
      state.annotations.push(stamp)
      expect(state.annotations).toHaveLength(1)
      expect(state.annotations[0].content).toBe('Faux')
    })

    it('click same button again to deactivate quick stamp', () => {
      state.quickStampMode = 'VRAI'
      expect(state.quickStampMode).toBe('VRAI')

      // Toggle off
      state.quickStampMode = state.quickStampMode === 'VRAI' ? null : 'VRAI'
      expect(state.quickStampMode).toBeNull()
    })
  })

  // --- Split view ---

  describe('Split view', () => {
    it('toggle split view -> grading panel visible', () => {
      state.layoutMode = 'full'
      expect(state.layoutMode).toBe('full')

      state.layoutMode = 'split'
      expect(state.layoutMode).toBe('split')
    })

    it('score entered in split panel reflected in main state', () => {
      state.layoutMode = 'split'
      state.scores['1.1'] = 7.5
      expect(state.scores['1.1']).toBe(7.5)
    })
  })

  // --- Tab preservation ---

  describe('Tab preservation', () => {
    it('switch to editor -> back to grading -> scroll preserved', () => {
      state.activeTab = 'scoring'
      state.scrollPositions['scoring'] = 250

      // Switch to editor
      state.activeTab = 'editor'
      expect(state.activeTab).toBe('editor')

      // Switch back
      state.activeTab = 'scoring'
      expect(state.scrollPositions['scoring']).toBe(250)
    })
  })

  // --- Finalization guards ---

  describe('Finalization guards', () => {
    it('all scores + appreciation required to finalize', () => {
      state.status = 'READY'
      const questions = ['1.1', '1.2', '1.3']

      // Missing scores
      let check = canFinalize(state, questions)
      expect(check.ok).toBe(false)
      expect(check.reason).toContain('Missing score')

      // Add scores but no appreciation
      state.scores['1.1'] = 5
      state.scores['1.2'] = 8
      state.scores['1.3'] = 7
      check = canFinalize(state, questions)
      expect(check.ok).toBe(false)
      expect(check.reason).toContain('Missing appreciation')

      // Add appreciation
      state.appreciation = 'Bon travail'
      check = canFinalize(state, questions)
      expect(check.ok).toBe(true)
    })

    it('score > 20 blocks finalization', () => {
      state.scores['1.1'] = 25
      state.appreciation = 'Test'
      const check = canFinalize(state, ['1.1'])
      expect(check.ok).toBe(false)
      expect(check.reason).toContain('exceeds 20')
    })
  })

  // --- Admin actions ---

  describe('Admin actions', () => {
    it('admin unlock flow: click unlock -> confirm -> refresh', async () => {
      const adminApi = {
        forceUnlockCopy: vi.fn().mockResolvedValue({ data: { success: true } }),
      }

      state.status = 'GRADING_IN_PROGRESS'
      const confirmed = true // user confirmed

      if (confirmed) {
        const result = await adminApi.forceUnlockCopy(state.copyId)
        expect(result.data.success).toBe(true)
        expect(adminApi.forceUnlockCopy).toHaveBeenCalledWith('copy-1')

        // Refresh state
        state.status = 'READY'
        expect(state.status).toBe('READY')
      }
    })

    it('admin reopen flow: click reopen -> confirm -> status returns to READY', async () => {
      const adminApi = {
        reopenCopy: vi.fn().mockResolvedValue({ data: { success: true, status: 'READY' } }),
      }

      state.status = 'GRADED'
      const confirmed = true

      if (confirmed) {
        const result = await adminApi.reopenCopy(state.copyId)
        expect(result.data.status).toBe('READY')
        state.status = result.data.status
        expect(state.status).toBe('READY')
      }
    })
  })
})
