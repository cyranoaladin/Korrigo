import { describe, it, expect, beforeEach, vi } from 'vitest'

/**
 * Progress Indicator Tests
 *
 * Tests the progress-tracking logic extracted from CorrectorDashboard.vue:
 *   - flattenLeafQuestions
 *   - getCopyProgress
 *   - Display / rendering helpers
 */

// --- Functions extracted from CorrectorDashboard.vue ---

interface Question {
  id: string
  label: string
  points: number
}

interface QuestionNode {
  id: string
  label?: string
  title?: string
  points?: number
  children?: QuestionNode[]
  sub_questions?: QuestionNode[]
}

interface Copy {
  id: string
  status: 'STAGING' | 'READY' | 'GRADING_IN_PROGRESS' | 'GRADED' | 'GRADING_FAILED'
  exam?: {
    id: string
    grading_structure: QuestionNode[]
  }
}

interface CopyProgress {
  scored: number
  total: number
  percent: number
  questions: (Question & { scored: boolean })[]
}

function flattenLeafQuestions(structure: QuestionNode[], prefix: string = ''): Question[] {
  const leaves: Question[] = []
  if (!Array.isArray(structure)) return leaves
  for (const item of structure) {
    const itemId = prefix ? `${prefix}.${item.id}` : item.id
    const children = item.children || item.sub_questions || []
    if (children.length > 0) {
      leaves.push(...flattenLeafQuestions(children, itemId))
    } else {
      leaves.push({
        id: itemId,
        label: item.label || item.title || itemId,
        points: item.points || 0,
      })
    }
  }
  return leaves
}

function getCopyProgress(
  copy: Copy,
  scoresData: Record<string, number | null> = {}
): CopyProgress {
  const structure = copy.exam?.grading_structure || []
  const leaves = flattenLeafQuestions(structure)
  const total = leaves.length

  if (copy.status === 'GRADED') {
    return {
      scored: total,
      total,
      percent: 100,
      questions: leaves.map((q) => ({ ...q, scored: true })),
    }
  }

  if (copy.status === 'STAGING') {
    return {
      scored: 0,
      total,
      percent: 0,
      questions: leaves.map((q) => ({ ...q, scored: false })),
    }
  }

  // READY or GRADING_IN_PROGRESS: count from scoresData
  const questions = leaves.map((q) => ({
    ...q,
    scored: scoresData[q.id] !== undefined && scoresData[q.id] !== null,
  }))
  const scored = questions.filter((q) => q.scored).length
  const percent = total > 0 ? Math.round((scored / total) * 100) : 0

  return { scored, total, percent, questions }
}

/** Format progress for display */
function formatProgress(progress: CopyProgress): string {
  return `${progress.scored}/${progress.total} questions notées`
}

/** Build progress bar segments */
function buildProgressSegments(progress: CopyProgress): { questionId: string; scored: boolean }[] {
  return progress.questions.map((q) => ({
    questionId: q.id,
    scored: q.scored,
  }))
}

// --------------------------------------------------------------------------
// Test data
// --------------------------------------------------------------------------

const nestedStructure: QuestionNode[] = [
  {
    id: '1',
    label: 'Exercice 1',
    points: 10,
    children: [
      { id: '1', label: 'Q1.1', points: 4 },
      { id: '2', label: 'Q1.2', points: 3 },
      {
        id: '3',
        label: 'Sous-partie',
        children: [
          { id: '1', label: 'Q1.3.1', points: 2 },
          { id: '2', label: 'Q1.3.2', points: 1 },
        ],
      },
    ],
  },
  {
    id: '2',
    label: 'Exercice 2',
    points: 10,
    children: [
      { id: '1', label: 'Q2.1', points: 5 },
      { id: '2', label: 'Q2.2', points: 3 },
      { id: '3', label: 'Q2.3', points: 2 },
    ],
  },
]

const singleLevelStructure: QuestionNode[] = [
  { id: '1', label: 'Question 1', points: 5 },
  { id: '2', label: 'Question 2', points: 5 },
  { id: '3', label: 'Question 3', points: 5 },
]

// --------------------------------------------------------------------------
// Tests
// --------------------------------------------------------------------------

describe('Progress Indicator', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // --- flattenLeafQuestions ---

  describe('flattenLeafQuestions', () => {
    it('extracts leaves from nested structure', () => {
      const leaves = flattenLeafQuestions(nestedStructure)
      expect(leaves).toHaveLength(7) // 2 + 2 (nested) + 3
      expect(leaves[0].id).toBe('1.1')
      expect(leaves[0].label).toBe('Q1.1')
      expect(leaves[0].points).toBe(4)
    })

    it('builds correct compound ids from nested levels', () => {
      const leaves = flattenLeafQuestions(nestedStructure)
      // 1.3.1 and 1.3.2 from the sub-part
      const deepLeaves = leaves.filter((l) => l.id.startsWith('1.3'))
      expect(deepLeaves).toHaveLength(2)
      expect(deepLeaves[0].id).toBe('1.3.1')
      expect(deepLeaves[1].id).toBe('1.3.2')
    })

    it('handles empty structure', () => {
      const leaves = flattenLeafQuestions([])
      expect(leaves).toHaveLength(0)
    })

    it('handles null/undefined gracefully', () => {
      const leaves = flattenLeafQuestions(null as any)
      expect(leaves).toHaveLength(0)
    })

    it('handles single-level structure (no nesting)', () => {
      const leaves = flattenLeafQuestions(singleLevelStructure)
      expect(leaves).toHaveLength(3)
      expect(leaves[0].id).toBe('1')
      expect(leaves[1].id).toBe('2')
      expect(leaves[2].id).toBe('3')
    })

    it('uses title field when label is missing', () => {
      const structure: QuestionNode[] = [
        { id: '1', title: 'Question via title', points: 5 },
      ]
      const leaves = flattenLeafQuestions(structure)
      expect(leaves[0].label).toBe('Question via title')
    })

    it('falls back to id when label and title are missing', () => {
      const structure: QuestionNode[] = [
        { id: '1', points: 5 },
      ]
      const leaves = flattenLeafQuestions(structure)
      expect(leaves[0].label).toBe('1')
    })

    it('handles sub_questions field (alternative child key)', () => {
      const structure: QuestionNode[] = [
        {
          id: '1',
          label: 'Ex',
          sub_questions: [
            { id: 'a', label: 'Q-a', points: 3 },
            { id: 'b', label: 'Q-b', points: 2 },
          ],
        },
      ]
      const leaves = flattenLeafQuestions(structure)
      expect(leaves).toHaveLength(2)
      expect(leaves[0].id).toBe('1.a')
    })

    it('defaults points to 0 when not specified', () => {
      const structure: QuestionNode[] = [{ id: '1', label: 'No points' }]
      const leaves = flattenLeafQuestions(structure)
      expect(leaves[0].points).toBe(0)
    })
  })

  // --- getCopyProgress ---

  describe('getCopyProgress', () => {
    it('returns 0% for STAGING copy', () => {
      const copy: Copy = {
        id: 'c1',
        status: 'STAGING',
        exam: { id: 'e1', grading_structure: nestedStructure },
      }

      const progress = getCopyProgress(copy)
      expect(progress.percent).toBe(0)
      expect(progress.scored).toBe(0)
      expect(progress.total).toBe(7)
      expect(progress.questions.every((q) => !q.scored)).toBe(true)
    })

    it('returns 100% for GRADED copy', () => {
      const copy: Copy = {
        id: 'c1',
        status: 'GRADED',
        exam: { id: 'e1', grading_structure: nestedStructure },
      }

      const progress = getCopyProgress(copy)
      expect(progress.percent).toBe(100)
      expect(progress.scored).toBe(7)
      expect(progress.questions.every((q) => q.scored)).toBe(true)
    })

    it('correctly counts scored questions for READY copy', () => {
      const copy: Copy = {
        id: 'c1',
        status: 'READY',
        exam: { id: 'e1', grading_structure: singleLevelStructure },
      }

      const scores = { '1': 5, '2': 3, '3': 4 }
      const progress = getCopyProgress(copy, scores)
      expect(progress.scored).toBe(3)
      expect(progress.total).toBe(3)
      expect(progress.percent).toBe(100)
    })

    it('handles partial scoring', () => {
      const copy: Copy = {
        id: 'c1',
        status: 'READY',
        exam: { id: 'e1', grading_structure: nestedStructure },
      }

      // Score only 3 of 7 questions
      const scores: Record<string, number | null> = {
        '1.1': 4,
        '1.2': 3,
        '2.1': 5,
      }
      const progress = getCopyProgress(copy, scores)
      expect(progress.scored).toBe(3)
      expect(progress.total).toBe(7)
      expect(progress.percent).toBe(43) // Math.round(3/7 * 100) = 43
    })

    it('null scores are not counted', () => {
      const copy: Copy = {
        id: 'c1',
        status: 'READY',
        exam: { id: 'e1', grading_structure: singleLevelStructure },
      }

      const scores: Record<string, number | null> = { '1': 5, '2': null, '3': 4 }
      const progress = getCopyProgress(copy, scores)
      expect(progress.scored).toBe(2)
      expect(progress.percent).toBe(67)
    })

    it('handles copy with no exam structure', () => {
      const copy: Copy = { id: 'c1', status: 'READY' }
      const progress = getCopyProgress(copy)
      expect(progress.total).toBe(0)
      expect(progress.scored).toBe(0)
      expect(progress.percent).toBe(0)
    })
  })

  // --- Progress display ---

  describe('Progress display', () => {
    it('shows "5/8 questions notées" format', () => {
      const progress: CopyProgress = {
        scored: 5,
        total: 8,
        percent: 63,
        questions: [],
      }
      expect(formatProgress(progress)).toBe('5/8 questions notées')
    })

    it('shows correct percentage', () => {
      const copy: Copy = {
        id: 'c1',
        status: 'READY',
        exam: { id: 'e1', grading_structure: nestedStructure },
      }
      const scores = { '1.1': 4, '1.2': 3, '1.3.1': 2, '1.3.2': 1, '2.1': 5 }
      const progress = getCopyProgress(copy, scores)
      expect(progress.percent).toBe(71) // 5/7 * 100 rounded
      expect(formatProgress(progress)).toBe('5/7 questions notées')
    })

    it('shows "0/3 questions notées" when nothing scored', () => {
      const progress: CopyProgress = {
        scored: 0,
        total: 3,
        percent: 0,
        questions: [],
      }
      expect(formatProgress(progress)).toBe('0/3 questions notées')
    })
  })

  // --- Progress bar segments ---

  describe('Progress bar segments', () => {
    it('renders correct number of segments', () => {
      const copy: Copy = {
        id: 'c1',
        status: 'READY',
        exam: { id: 'e1', grading_structure: singleLevelStructure },
      }
      const progress = getCopyProgress(copy, { '1': 5, '2': 3 })
      const segments = buildProgressSegments(progress)
      expect(segments).toHaveLength(3)
    })

    it('colored segments match scored questions', () => {
      const copy: Copy = {
        id: 'c1',
        status: 'READY',
        exam: { id: 'e1', grading_structure: singleLevelStructure },
      }
      const progress = getCopyProgress(copy, { '1': 5, '3': 4 })
      const segments = buildProgressSegments(progress)

      expect(segments[0]).toEqual({ questionId: '1', scored: true })
      expect(segments[1]).toEqual({ questionId: '2', scored: false })
      expect(segments[2]).toEqual({ questionId: '3', scored: true })
    })

    it('all segments scored for GRADED copy', () => {
      const copy: Copy = {
        id: 'c1',
        status: 'GRADED',
        exam: { id: 'e1', grading_structure: singleLevelStructure },
      }
      const progress = getCopyProgress(copy)
      const segments = buildProgressSegments(progress)

      expect(segments.every((s) => s.scored)).toBe(true)
    })

    it('no segments scored for STAGING copy', () => {
      const copy: Copy = {
        id: 'c1',
        status: 'STAGING',
        exam: { id: 'e1', grading_structure: singleLevelStructure },
      }
      const progress = getCopyProgress(copy)
      const segments = buildProgressSegments(progress)

      expect(segments.every((s) => !s.scored)).toBe(true)
    })

    it('empty structure yields zero segments', () => {
      const copy: Copy = {
        id: 'c1',
        status: 'READY',
        exam: { id: 'e1', grading_structure: [] },
      }
      const progress = getCopyProgress(copy)
      const segments = buildProgressSegments(progress)
      expect(segments).toHaveLength(0)
    })
  })
})
