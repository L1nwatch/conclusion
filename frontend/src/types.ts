export type Confidence = 'High' | 'Medium' | 'Low'

export interface TimeHorizonAnswers {
  tenHours: string
  tenDays: string
  tenMonths: string
  tenYears: string
}

export interface ScenarioAnswers {
  bestCase: string
  likelyCase: string
  worstCase: string
  safeguards: string
}

export interface MungerChecklistAnswers {
  incentives: string
  opportunityCost: string
  inversion: string
  secondOrderEffects: string
  circleOfCompetence: string
  disconfirmingEvidence: string
}

export type DecisionModelRun =
  | { modelId: 'time-horizons'; answers: TimeHorizonAnswers }
  | { modelId: 'scenario-range'; answers: ScenarioAnswers }
  | { modelId: 'munger-checklist'; answers: MungerChecklistAnswers }

export interface DecisionAnalysis {
  version: 1
  models: DecisionModelRun[]
}

export interface ConclusionRecord {
  id: number
  title: string
  question: string
  conclusion: string
  reason: string
  tradeoffs: string
  conditions: string
  category: string
  tags: string[]
  confidence: Confidence
  decisionAnalysis: DecisionAnalysis
  createdAt: string
  updatedAt: string
}

export type ConclusionInput = Omit<ConclusionRecord, 'id' | 'createdAt' | 'updatedAt'>

export type ConclusionUpdateInput = Partial<ConclusionInput> & {
  expectedUpdatedAt: string
}

export interface ConclusionListResponse {
  count: number
  returned: number
  items: ConclusionRecord[]
}
