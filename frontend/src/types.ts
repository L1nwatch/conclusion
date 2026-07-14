export type Confidence = 'High' | 'Medium' | 'Low'

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
