import { describe, expect, it } from 'vitest'

import {
  computeMaxTotalScore,
  formatScoreLimit,
  getScoreOverflowMessage,
} from '../../src/utils/correctorDeskScoreLimits'

describe('correctorDeskScoreLimits', () => {
  it('computes the maximum total score from flat questions', () => {
    const maxTotal = computeMaxTotalScore([
      { maxScore: 6 },
      { maxScore: 3.5 },
      { maxScore: 4.5 },
    ])

    expect(maxTotal).toBe(14)
  })

  it('formats score limits with two decimals for display', () => {
    expect(formatScoreLimit(14)).toBe('14.00')
    expect(formatScoreLimit(17.5)).toBe('17.50')
  })

  it('builds an overflow message from the real maximum instead of a hard-coded 20', () => {
    expect(getScoreOverflowMessage(14)).toBe('D\u00e9passe le maximum autoris\u00e9 (14.00).')
  })
})
