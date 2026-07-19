import type { DecisionAnalysis, DecisionModelDefinition } from './types'

export function emptyDecisionAnalysis(
  definitions: DecisionModelDefinition[],
): DecisionAnalysis {
  return {
    version: 1,
    models: definitions.map((definition) => ({
      modelId: definition.id,
      modelVersion: definition.version,
      answers: { analysis: '' },
    })),
  }
}

export function compactDecisionAnalysis(analysis: DecisionAnalysis): DecisionAnalysis {
  return {
    version: 1,
    models: analysis.models
      .map((model) => ({
        ...model,
        answers: Object.fromEntries(
          Object.entries(model.answers).filter(([, answer]) => answer.trim()),
        ),
      }))
      .filter((model) => Object.keys(model.answers).length > 0),
  }
}

export function hydrateDecisionAnalysis(
  analysis: DecisionAnalysis,
  definitions: DecisionModelDefinition[],
): DecisionAnalysis {
  const hydrated = emptyDecisionAnalysis(definitions)
  for (const saved of analysis.models) {
    const target = hydrated.models.find(
      (model) =>
        model.modelId === saved.modelId && model.modelVersion === saved.modelVersion,
    )
    if (target) Object.assign(target.answers, saved.answers)
  }
  return hydrated
}
