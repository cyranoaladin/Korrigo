/**
 * Regression tests for annotation mode mutual exclusion.
 *
 * Root cause (commit 4effc50): quickStampMode and preSelectedAnnotationType
 * were two independent refs. Activating one did NOT deactivate the other,
 * so quickStampMode (checked first via ||) silently overrode annotation types.
 *
 * Fix: single `annotationMode` ref with { group, value }.
 * These tests verify the structural guarantee.
 */
import { describe, it, expect } from 'vitest'
import { ref, computed } from 'vue'

// --- Mirror of production logic (CorrectorDesk.vue lines 49-61) ---
function createAnnotationMode() {
  const annotationMode = ref<{ group: string | null; value: string | null }>({ group: null, value: null })

  const setAnnotationMode = (group: string, value: string) => {
    if (annotationMode.value.group === group && annotationMode.value.value === value) {
      annotationMode.value = { group: null, value: null }
    } else {
      annotationMode.value = { group, value }
    }
  }

  const quickStampMode = computed(() =>
    annotationMode.value.group === 'stamp' ? annotationMode.value.value : null
  )
  const preSelectedAnnotationType = computed(() =>
    annotationMode.value.group === 'type' ? annotationMode.value.value : null
  )

  return { annotationMode, setAnnotationMode, quickStampMode, preSelectedAnnotationType }
}

describe('Annotation Mode — Mutual Exclusion', () => {
  it('starts with no mode active', () => {
    const { quickStampMode, preSelectedAnnotationType } = createAnnotationMode()
    expect(quickStampMode.value).toBeNull()
    expect(preSelectedAnnotationType.value).toBeNull()
  })

  it('activating stamp clears annotation type', () => {
    const { setAnnotationMode, quickStampMode, preSelectedAnnotationType } = createAnnotationMode()
    setAnnotationMode('type', 'COMMENTAIRE')
    expect(preSelectedAnnotationType.value).toBe('COMMENTAIRE')

    setAnnotationMode('stamp', 'FAUX')
    expect(quickStampMode.value).toBe('FAUX')
    expect(preSelectedAnnotationType.value).toBeNull()
  })

  it('activating annotation type clears stamp', () => {
    const { setAnnotationMode, quickStampMode, preSelectedAnnotationType } = createAnnotationMode()
    setAnnotationMode('stamp', 'VRAI')
    expect(quickStampMode.value).toBe('VRAI')

    setAnnotationMode('type', 'ERREUR')
    expect(preSelectedAnnotationType.value).toBe('ERREUR')
    expect(quickStampMode.value).toBeNull()
  })

  it('toggling same mode deactivates it', () => {
    const { setAnnotationMode, quickStampMode } = createAnnotationMode()
    setAnnotationMode('stamp', 'FAUX')
    expect(quickStampMode.value).toBe('FAUX')

    setAnnotationMode('stamp', 'FAUX')
    expect(quickStampMode.value).toBeNull()
  })

  it('switching within same group changes value', () => {
    const { setAnnotationMode, preSelectedAnnotationType } = createAnnotationMode()
    setAnnotationMode('type', 'COMMENTAIRE')
    expect(preSelectedAnnotationType.value).toBe('COMMENTAIRE')

    setAnnotationMode('type', 'SURLIGNAGE')
    expect(preSelectedAnnotationType.value).toBe('SURLIGNAGE')
  })

  it('CRITICAL: FAUX then COMMENTAIRE — drawing must NOT produce FAUX', () => {
    const { setAnnotationMode, quickStampMode, preSelectedAnnotationType } = createAnnotationMode()

    // User clicks FAUX
    setAnnotationMode('stamp', 'FAUX')
    expect(quickStampMode.value).toBe('FAUX')

    // User clicks Commentaire
    setAnnotationMode('type', 'COMMENTAIRE')

    // FAUX must be gone — this is the exact regression scenario
    expect(quickStampMode.value).toBeNull()
    expect(preSelectedAnnotationType.value).toBe('COMMENTAIRE')
  })

  it('CRITICAL: VRAI then ERREUR — drawing must NOT produce VRAI', () => {
    const { setAnnotationMode, quickStampMode, preSelectedAnnotationType } = createAnnotationMode()

    setAnnotationMode('stamp', 'VRAI')
    setAnnotationMode('type', 'ERREUR')

    expect(quickStampMode.value).toBeNull()
    expect(preSelectedAnnotationType.value).toBe('ERREUR')
  })

  it('rapid switching never has both active', () => {
    const { setAnnotationMode, quickStampMode, preSelectedAnnotationType } = createAnnotationMode()
    const sequence = [
      ['stamp', 'VRAI'], ['type', 'BONUS'], ['stamp', 'FAUX'],
      ['type', 'SURLIGNAGE'], ['type', 'COMMENTAIRE'], ['stamp', 'VRAI'],
    ] as const

    for (const [group, value] of sequence) {
      setAnnotationMode(group, value)
      // Invariant: at most one group active at any time
      const bothActive = quickStampMode.value !== null && preSelectedAnnotationType.value !== null
      expect(bothActive).toBe(false)
    }
  })

  it('all 6 annotation values work correctly', () => {
    const { setAnnotationMode, quickStampMode, preSelectedAnnotationType } = createAnnotationMode()

    setAnnotationMode('stamp', 'VRAI')
    expect(quickStampMode.value).toBe('VRAI')

    setAnnotationMode('stamp', 'FAUX')
    expect(quickStampMode.value).toBe('FAUX')

    setAnnotationMode('type', 'COMMENTAIRE')
    expect(preSelectedAnnotationType.value).toBe('COMMENTAIRE')

    setAnnotationMode('type', 'SURLIGNAGE')
    expect(preSelectedAnnotationType.value).toBe('SURLIGNAGE')

    setAnnotationMode('type', 'ERREUR')
    expect(preSelectedAnnotationType.value).toBe('ERREUR')

    setAnnotationMode('type', 'BONUS')
    expect(preSelectedAnnotationType.value).toBe('BONUS')
  })
})
