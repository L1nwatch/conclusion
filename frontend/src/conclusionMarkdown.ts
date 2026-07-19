import type { ConclusionRecord, DecisionModelDefinition } from './types'

export function conclusionMarkdown(
  record: ConclusionRecord,
  definitions: DecisionModelDefinition[],
): string {
  const sections = [record.reason.trim()]

  if (record.question.trim() && record.question.trim() !== record.title.trim()) {
    sections.push(`## 原始问题\n\n${record.question.trim()}`)
  }
  if (record.tradeoffs.trim()) {
    sections.push(`## 接受的取舍\n\n${record.tradeoffs.trim()}`)
  }
  if (record.conditions.trim()) {
    sections.push(`## 重新评估条件\n\n${record.conditions.trim()}`)
  }

  const analyses = record.decisionAnalysis.models.flatMap((run) => {
    const content = (
      run.answers.analysis?.trim() ||
      Object.values(run.answers).filter((answer) => answer.trim()).join('\n\n')
    ).trim()
    if (!content) return []
    const name =
      definitions.find(
        (definition) =>
          definition.id === run.modelId && definition.version === run.modelVersion,
      )?.name ?? run.modelId
    return [`### ${name}\n\n${content}`]
  })
  if (analyses.length) sections.push(`## 思考过程\n\n${analyses.join('\n\n')}`)

  return sections.filter(Boolean).join('\n\n')
}
