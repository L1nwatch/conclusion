import { describe, expect, it } from 'vitest'
import {
  compactDecisionAnalysis,
  emptyDecisionAnalysis,
  hydrateDecisionAnalysis,
} from './decisionModels'
import type { DecisionModelDefinition } from './types'

const definition: DecisionModelDefinition = {
  id: 'constraint-check',
  version: 1,
  name: '约束检查',
  explanation: '找出决定必须满足的硬约束。',
  isBuiltin: false,
  createdAt: '2026-07-14T12:00:00Z',
  updatedAt: '2026-07-14T12:00:00Z',
}

describe('dynamic decision model analysis', () => {
  it('creates one short analysis slot for each model', () => {
    expect(emptyDecisionAnalysis([definition])).toEqual({
      version: 1,
      models: [
        {
          modelId: 'constraint-check',
          modelVersion: 1,
          answers: { analysis: '' },
        },
      ],
    })
  })

  it('hydrates a saved analysis and compacts blank models before writing', () => {
    const hydrated = hydrateDecisionAnalysis(
      {
        version: 1,
        models: [
          {
            modelId: 'constraint-check',
            modelVersion: 1,
            answers: { analysis: '不能超出每周时间预算' },
          },
        ],
      },
      [definition],
    )

    expect(hydrated.models[0]?.answers).toEqual({
      analysis: '不能超出每周时间预算',
    })
    expect(compactDecisionAnalysis(hydrated)).toEqual({
      version: 1,
      models: [
        {
          modelId: 'constraint-check',
          modelVersion: 1,
          answers: { analysis: '不能超出每周时间预算' },
        },
      ],
    })
  })
})
