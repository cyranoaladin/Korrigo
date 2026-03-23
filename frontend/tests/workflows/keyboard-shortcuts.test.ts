import { describe, it, expect, beforeEach, vi } from 'vitest'

/**
 * Keyboard Shortcuts Tests
 *
 * Tests the keyboard shortcut handler logic extracted from CorrectorDeskV2.vue.
 * All tests run in-memory against a pure-function handler, no DOM rendering needed.
 */

// --- Handler extracted from CorrectorDeskV2 onGlobalKeydown logic ---

interface KeyboardState {
  currentPage: number
  totalPages: number
  showEditor: boolean
  isTyping: boolean
  layoutMode: 'split' | 'full' | 'focus'
  quickStampMode: string | null
  annotations: any[]
}

type Action =
  | 'prevPage'
  | 'nextPage'
  | 'cancelEditor'
  | 'saveAnnotation'
  | 'toggleFocus'
  | 'quickAnnotation'
  | 'none'

interface KeyEvent {
  key: string
  ctrlKey?: boolean
  metaKey?: boolean
  shiftKey?: boolean
}

function handleKeydown(state: KeyboardState, event: KeyEvent): Action {
  const { key, ctrlKey = false, metaKey = false } = event

  // When typing in an input, only allow Escape and Ctrl+Enter in editor mode
  if (state.isTyping) {
    if (state.showEditor && key === 'Escape') return 'cancelEditor'
    if (state.showEditor && (ctrlKey || metaKey) && key === 'Enter') return 'saveAnnotation'
    return 'none'
  }

  // Editor-specific shortcuts
  if (state.showEditor) {
    if (key === 'Escape') return 'cancelEditor'
    if ((ctrlKey || metaKey) && key === 'Enter') return 'saveAnnotation'
    return 'none'
  }

  // Focus mode toggle
  if ((ctrlKey || metaKey) && key === 'F') {
    return 'toggleFocus'
  }

  // Quick annotation shortcut (Ctrl + shortcut key)
  if (ctrlKey && state.layoutMode !== 'focus') {
    const quickKeys = ['f', 'v', 'r', 'b', 'i']
    if (quickKeys.includes(key.toLowerCase())) {
      return 'quickAnnotation'
    }
  }

  // Page navigation
  if (key === 'ArrowLeft' || key === 'PageUp') return 'prevPage'
  if (key === 'ArrowRight' || key === 'PageDown') return 'nextPage'

  return 'none'
}

function applyPageNav(state: KeyboardState, action: 'prevPage' | 'nextPage'): void {
  if (action === 'prevPage' && state.currentPage > 1) {
    state.currentPage--
  } else if (action === 'nextPage' && state.currentPage < state.totalPages) {
    state.currentPage++
  }
}

// --------------------------------------------------------------------------
// Tests
// --------------------------------------------------------------------------

describe('Keyboard Shortcuts', () => {
  let state: KeyboardState

  beforeEach(() => {
    vi.clearAllMocks()
    state = {
      currentPage: 2,
      totalPages: 5,
      showEditor: false,
      isTyping: false,
      layoutMode: 'split',
      quickStampMode: null,
      annotations: [],
    }
  })

  // --- Page navigation ---

  describe('Page navigation', () => {
    it('ArrowLeft navigates to previous page', () => {
      const action = handleKeydown(state, { key: 'ArrowLeft' })
      expect(action).toBe('prevPage')
      applyPageNav(state, 'prevPage')
      expect(state.currentPage).toBe(1)
    })

    it('ArrowRight navigates to next page', () => {
      const action = handleKeydown(state, { key: 'ArrowRight' })
      expect(action).toBe('nextPage')
      applyPageNav(state, 'nextPage')
      expect(state.currentPage).toBe(3)
    })

    it('PageUp navigates to previous page', () => {
      const action = handleKeydown(state, { key: 'PageUp' })
      expect(action).toBe('prevPage')
      applyPageNav(state, 'prevPage')
      expect(state.currentPage).toBe(1)
    })

    it('PageDown navigates to next page', () => {
      const action = handleKeydown(state, { key: 'PageDown' })
      expect(action).toBe('nextPage')
      applyPageNav(state, 'nextPage')
      expect(state.currentPage).toBe(3)
    })

    it('ArrowLeft at page 1 does not go below 1', () => {
      state.currentPage = 1
      applyPageNav(state, 'prevPage')
      expect(state.currentPage).toBe(1)
    })

    it('ArrowRight at last page does not exceed totalPages', () => {
      state.currentPage = 5
      applyPageNav(state, 'nextPage')
      expect(state.currentPage).toBe(5)
    })
  })

  // --- Editor shortcuts ---

  describe('Editor shortcuts', () => {
    it('Escape cancels annotation editor', () => {
      state.showEditor = true
      const action = handleKeydown(state, { key: 'Escape' })
      expect(action).toBe('cancelEditor')
    })

    it('Ctrl+Enter saves annotation from editor', () => {
      state.showEditor = true
      const action = handleKeydown(state, { key: 'Enter', ctrlKey: true })
      expect(action).toBe('saveAnnotation')
    })

    it('Meta+Enter (Mac) saves annotation from editor', () => {
      state.showEditor = true
      const action = handleKeydown(state, { key: 'Enter', metaKey: true })
      expect(action).toBe('saveAnnotation')
    })

    it('non-Escape/Ctrl+Enter keys are blocked when editor open', () => {
      state.showEditor = true
      expect(handleKeydown(state, { key: 'ArrowLeft' })).toBe('none')
      expect(handleKeydown(state, { key: 'ArrowRight' })).toBe('none')
      expect(handleKeydown(state, { key: 'PageUp' })).toBe('none')
      expect(handleKeydown(state, { key: 'a' })).toBe('none')
    })
  })

  // --- Text input blocking ---

  describe('Text input blocking', () => {
    it('keyboard shortcuts disabled during text input', () => {
      state.isTyping = true
      expect(handleKeydown(state, { key: 'ArrowLeft' })).toBe('none')
      expect(handleKeydown(state, { key: 'ArrowRight' })).toBe('none')
      expect(handleKeydown(state, { key: 'PageUp' })).toBe('none')
      expect(handleKeydown(state, { key: 'PageDown' })).toBe('none')
    })

    it('Escape still works during text input when editor is open', () => {
      state.isTyping = true
      state.showEditor = true
      expect(handleKeydown(state, { key: 'Escape' })).toBe('cancelEditor')
    })

    it('Ctrl+Enter still works during text input when editor is open', () => {
      state.isTyping = true
      state.showEditor = true
      expect(handleKeydown(state, { key: 'Enter', ctrlKey: true })).toBe('saveAnnotation')
    })

    it('Escape does nothing during text input without editor', () => {
      state.isTyping = true
      state.showEditor = false
      expect(handleKeydown(state, { key: 'Escape' })).toBe('none')
    })
  })

  // --- Quick annotation shortcuts ---

  describe('Quick annotation shortcuts', () => {
    it('Ctrl+F triggers quickAnnotation for Faux', () => {
      // Note: Ctrl+F uppercase triggers toggleFocus, Ctrl+f lowercase triggers quick annotation
      const action = handleKeydown(state, { key: 'f', ctrlKey: true })
      expect(action).toBe('quickAnnotation')
    })

    it('Ctrl+v triggers quickAnnotation for Vrai', () => {
      const action = handleKeydown(state, { key: 'v', ctrlKey: true })
      expect(action).toBe('quickAnnotation')
    })

    it('quick annotation shortcuts disabled in focus mode', () => {
      state.layoutMode = 'focus'
      const action = handleKeydown(state, { key: 'f', ctrlKey: true })
      // In focus mode, Ctrl+f does not match quickAnnotation
      expect(action).not.toBe('quickAnnotation')
    })
  })

  // --- Focus mode toggle ---

  describe('Focus mode toggle', () => {
    it('Ctrl+F (uppercase) toggles focus mode', () => {
      const action = handleKeydown(state, { key: 'F', ctrlKey: true })
      expect(action).toBe('toggleFocus')
    })
  })

  // --- Unrecognized keys ---

  describe('Unrecognized keys', () => {
    it('random keys produce no action', () => {
      expect(handleKeydown(state, { key: 'z' })).toBe('none')
      expect(handleKeydown(state, { key: '1' })).toBe('none')
      expect(handleKeydown(state, { key: 'Tab' })).toBe('none')
    })
  })
})
