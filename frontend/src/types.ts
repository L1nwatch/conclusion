export type Confidence = 'High' | 'Medium' | 'Low'

export interface DecisionModelDefinition {
  id: string
  version: number
  name: string
  explanation: string
  isBuiltin: boolean
  createdAt: string
  updatedAt: string
}

export interface DecisionModelListResponse {
  count: number
  items: DecisionModelDefinition[]
}

export interface DecisionModelCreateInput {
  id: string
  name: string
  explanation: string
}

export interface DecisionModelUpdateInput {
  name: string
  explanation: string
  expectedVersion: number
}

export interface DecisionModelRun {
  modelId: string
  modelVersion: number
  answers: Record<string, string>
}

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
