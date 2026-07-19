import { describe, expect, it } from 'vitest'
import { conclusionMarkdown } from './conclusionMarkdown'
import type { ConclusionRecord, DecisionModelDefinition } from './types'

const record: ConclusionRecord = {
  id: 1,
  title: '暂不更换书桌',
  question: '是否现在购买升降桌？',
  conclusion: '等现有书桌影响使用时再更换。',
  reason: '当前改善有限，不值得立即占用预算。',
  tradeoffs: '暂时接受高度不够理想。',
  conditions: '现有书桌影响坐姿时重新评估。',
  category: '购物',
  tags: [],
  confidence: 'Medium',
  decisionAnalysis: {
    version: 1,
    models: [
      {
        modelId: 'time-horizons',
        modelVersion: 1,
        answers: { analysis: '十个月后，购买时点本身并不重要。' },
      },
    ],
  },
  createdAt: '2026-07-14T12:00:00Z',
  updatedAt: '2026-07-14T12:00:00Z',
}

const definition: DecisionModelDefinition = {
  id: 'time-horizons',
  version: 1,
  name: '时间尺度',
  explanation: '从多个时间尺度回看决定。',
  isBuiltin: true,
  createdAt: record.createdAt,
  updatedAt: record.updatedAt,
}

describe('conclusion Markdown detail', () => {
  it('folds legacy fields and model analysis into one Markdown document', () => {
    expect(conclusionMarkdown(record, [definition])).toContain(
      '## 原始问题\n\n是否现在购买升降桌？',
    )
    expect(conclusionMarkdown(record, [definition])).toContain(
      '## 思考过程\n\n### 时间尺度\n\n十个月后，购买时点本身并不重要。',
    )
  })

  it('keeps a simple record as just its Markdown detail', () => {
    expect(
      conclusionMarkdown(
        {
          ...record,
          question: record.conclusion,
          tradeoffs: '',
          conditions: '',
          decisionAnalysis: { version: 1, models: [] },
        },
        [],
      ),
    ).toBe(record.reason)
  })
})
