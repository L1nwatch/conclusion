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
  shortName: 'CONSTRAINTS',
  description: '找出决定必须满足的硬约束。',
  prompts: [
    { key: 'hardConstraints', label: '硬约束', placeholder: '' },
    { key: 'bottleneck', label: '瓶颈', placeholder: '' },
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
          modelId: 'constraint-check',
          modelVersion: 1,
          answers: { hardConstraints: '', bottleneck: '' },
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
            modelId: 'constraint-check',
            modelVersion: 1,
            answers: { hardConstraints: '不能超出每周时间预算' },
          },
        ],
      },
      [definition],
    )

    expect(hydrated.models[0]?.answers).toEqual({
      hardConstraints: '不能超出每周时间预算',
      bottleneck: '',
    })
    expect(compactDecisionAnalysis(hydrated)).toEqual({
      version: 1,
      models: [
        {
          modelId: 'constraint-check',
          modelVersion: 1,
          answers: { hardConstraints: '不能超出每周时间预算' },
        },
      ],
    })
  })
})
