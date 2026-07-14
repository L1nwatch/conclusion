import type { DecisionAnalysis, DecisionModelRun } from './types'

export type DecisionModelId = DecisionModelRun['modelId']

export interface DecisionPrompt {
  key: string
  label: string
  placeholder: string
}

export interface DecisionModelDefinition {
  id: DecisionModelId
  name: string
  shortName: string
  description: string
  prompts: DecisionPrompt[]
}

export const decisionModels: DecisionModelDefinition[] = [
  {
    id: 'time-horizons',
    name: '时间尺度',
    shortName: '10H · 10D · 10M · 10Y',
    description: '把眼前情绪拉远，观察这个决定在不同时间尺度上的影响。',
    prompts: [
      { key: 'tenHours', label: '10 小时后', placeholder: '今天晚些时候，我会怎么看？' },
      { key: 'tenDays', label: '10 天后', placeholder: '短期影响会是什么？' },
      { key: 'tenMonths', label: '10 个月后', placeholder: '它会带来什么持续变化？' },
      { key: 'tenYears', label: '10 年后', placeholder: '长期回看，什么真正重要？' },
    ],
  },
  {
    id: 'scenario-range',
    name: '情景边界',
    shortName: 'BEST · LIKELY · WORST',
    description: '同时看到上行空间、最可能结果和可以承受的下行风险。',
    prompts: [
      { key: 'bestCase', label: '最好情况', placeholder: '合理范围内，最好会发生什么？' },
      { key: 'likelyCase', label: '最可能情况', placeholder: '不乐观也不悲观，最可能怎样？' },
      { key: 'worstCase', label: '最坏情况', placeholder: '合理的最坏结果是什么？' },
      { key: 'safeguards', label: '保护措施', placeholder: '如何降低损失，或者保留退路？' },
    ],
  },
  {
    id: 'munger-checklist',
    name: '芒格式多模型检查',
    shortName: 'LATTICEWORK CHECK',
    description: '受多模型思维启发，从激励、反演和认知盲点检查遗漏。',
    prompts: [
      { key: 'incentives', label: '激励', placeholder: '谁希望我做什么？各方真实激励是什么？' },
      { key: 'opportunityCost', label: '机会成本', placeholder: '选择它，就放弃了什么更好的用途？' },
      { key: 'inversion', label: '反演', placeholder: '怎样做几乎一定会失败？现在是否正在这样做？' },
      { key: 'secondOrderEffects', label: '二阶效应', placeholder: '然后呢？这个结果还会继续导致什么？' },
      { key: 'circleOfCompetence', label: '能力圈', placeholder: '我真正知道什么？哪些只是在猜？' },
      { key: 'disconfirmingEvidence', label: '反方证据', placeholder: '什么事实会证明我错了？我是否主动找过？' },
    ],
  },
]

export function emptyDecisionAnalysis(): DecisionAnalysis {
  return {
    version: 1,
    models: [
      {
        modelId: 'time-horizons',
        answers: { tenHours: '', tenDays: '', tenMonths: '', tenYears: '' },
      },
      {
        modelId: 'scenario-range',
        answers: { bestCase: '', likelyCase: '', worstCase: '', safeguards: '' },
      },
      {
        modelId: 'munger-checklist',
        answers: {
          incentives: '',
          opportunityCost: '',
          inversion: '',
          secondOrderEffects: '',
          circleOfCompetence: '',
          disconfirmingEvidence: '',
        },
      },
    ],
  }
}

export function compactDecisionAnalysis(analysis: DecisionAnalysis): DecisionAnalysis {
  return {
    version: 1,
    models: analysis.models.filter((model) =>
      Object.values(model.answers).some((answer) => answer.trim()),
    ),
  }
}

export function hydrateDecisionAnalysis(analysis: DecisionAnalysis): DecisionAnalysis {
  const hydrated = emptyDecisionAnalysis()
  for (const saved of analysis.models) {
    const target = hydrated.models.find((model) => model.modelId === saved.modelId)
    if (target) Object.assign(target.answers, saved.answers)
  }
  return hydrated
}
