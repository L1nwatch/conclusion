export type Confidence = 'High' | 'Medium' | 'Low'

export interface ConclusionRecord {
  id: number
  title: string
  question: string
  conclusion: string
  reason: string
  tradeoffs: string
  category: string
  confidence: Confidence
  createdAt: string
  updatedAt: string
}

export interface ConclusionListResponse {
  count: number
  returned: number
  items: ConclusionRecord[]
}

