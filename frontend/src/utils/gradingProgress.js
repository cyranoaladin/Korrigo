export function computeGradingProgress(flatQuestions, questionScores) {
  const questions = Array.isArray(flatQuestions) ? flatQuestions : []
  const entries = questionScores instanceof Map ? questionScores : new Map(Object.entries(questionScores || {}))

  const total = questions.length
  const detailed = questions.map((question) => {
    const value = entries.get(question.id)
    const scored = value !== null && value !== undefined && value !== ''
    return { ...question, scored }
  })
  const scored = detailed.filter((question) => question.scored).length
  const percent = total > 0 ? Math.round((scored / total) * 100) : 0

  return {
    scored,
    total,
    percent,
    remaining: Math.max(total - scored, 0),
    questions: detailed,
  }
}
