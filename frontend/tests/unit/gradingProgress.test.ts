import { describe, it, expect } from 'vitest'

import { computeGradingProgress } from '../../src/utils/gradingProgress'

describe('computeGradingProgress', () => {
  it('computes scored, remaining and percent from a question map', () => {
    const progress = computeGradingProgress(
      [
        { id: 'Q1', label: 'Q1', points: 5 },
        { id: 'Q2', label: 'Q2', points: 5 },
        { id: 'Q3', label: 'Q3', points: 5 },
      ],
      new Map([
        ['Q1', 4],
        ['Q2', null],
        ['Q3', 3],
      ]),
    )

    expect(progress.scored).toBe(2)
    expect(progress.total).toBe(3)
    expect(progress.remaining).toBe(1)
    expect(progress.percent).toBe(67)
    expect(progress.questions[1].scored).toBe(false)
  })
})
