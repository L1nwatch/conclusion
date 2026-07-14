import { describe, expect, it } from 'vitest'
import {
  compactDecisionAnalysis,
  emptyDecisionAnalysis,
  hydrateDecisionAnalysis,
} from './decisionModels'
import type { DecisionModelDefinition } from './types'

const definition: DecisionModelDefinition = {
  id: 'reversibility',
  version: 1,
  name: '可逆性检查',
  shortName: 'ONE-WAY · TWO-WAY',
  description: '判断决定是否容易撤销。',
  prompts: [
    { key: 'reversible', label: '是否可逆', placeholder: '' },
    { key: 'exitCost', label: '退出成本', placeholder: '' },
  ],
  sourceName: '',
  sourceUrl: '',
  isBuiltin: false,
  createdAt: '2026-07-14T12:00:00Z',
  updatedAt: '2026-07-14T12:00:00Z',
}

describe('dynamic decision model analysis', () => {
  it('creates empty answer slots from a registry definition', () => {
    expect(emptyDecisionAnalysis([definition])).toEqual({
      version: 1,
      models: [
        {
          modelId: 'reversibility',
          modelVersion: 1,
          answers: { reversible: '', exitCost: '' },
        },
      ],
    })
  })

  it('hydrates saved answers and compacts blank prompts before writing', () => {
    const hydrated = hydrateDecisionAnalysis(
      {
        version: 1,
        models: [
          {
            modelId: 'reversibility',
            modelVersion: 1,
            answers: { reversible: '可以撤销' },
          },
        ],
      },
      [definition],
    )

    expect(hydrated.models[0]?.answers).toEqual({
      reversible: '可以撤销',
      exitCost: '',
    })
    expect(compactDecisionAnalysis(hydrated)).toEqual({
      version: 1,
      models: [
        {
          modelId: 'reversibility',
          modelVersion: 1,
          answers: { reversible: '可以撤销' },
        },
      ],
    })
  })
})
