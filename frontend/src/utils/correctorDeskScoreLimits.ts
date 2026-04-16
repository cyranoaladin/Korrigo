type FlatQuestionLike = {
  maxScore?: number | string | null
}

function toNumericScore(value: number | string | null | undefined): number {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

export function computeMaxTotalScore(questions: FlatQuestionLike[]): number {
  return questions.reduce((sum, question) => sum + toNumericScore(question?.maxScore), 0)
}

export function formatScoreLimit(limit: number): string {
  return toNumericScore(limit).toFixed(2)
}

export function getScoreOverflowMessage(limit: number): string {
  return `Dépasse le maximum autorisé (${formatScoreLimit(limit)}).`
}
