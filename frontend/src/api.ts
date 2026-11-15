import type {
  ConclusionInput,
  ConclusionListResponse,
  ConclusionRecord,
  ConclusionUpdateInput,
  DecisionModelListResponse,
  DecisionModelCreateInput,
  DecisionModelDefinition,
  DecisionModelUpdateInput,
} from './types'
import type { DecisionDetails, DecisionNode, DecisionRecord, DecisionStatus, DecisionSummary } from './decisionTree'

const apiBase = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly body: unknown,
  ) {
    super(message)
  }
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(`${apiBase}${path}`, init)
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const decision = /^\/api\/decisions(?:[/?]|$)/.test(path)
    let message = '请求没有成功，请稍后重试'
    if (response.status === 404) {
      message = decision ? '没有找到这条决策' : '没有找到这条结论'
    } else if (response.status === 409) {
      message = decision ? '这条决策已更新。请重新加载最新版本后再保存。' : '这条结论已经被其他写入者更新'
    } else if (decision && typeof body?.detail === 'string') {
      message = body.detail
    }
    throw new ApiError(message, response.status, body)
  }
  return response
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await request(path, init)
  return response.json() as Promise<T>
}

export function listConclusions(limit = 100): Promise<ConclusionListResponse> {
  return requestJson(`/api/conclusions?limit=${limit}`)
}

export function getConclusion(id: number): Promise<ConclusionRecord> {
  return requestJson(`/api/conclusions/${id}`)
}

export function listDecisionModels(includeDeleted = false): Promise<DecisionModelListResponse> {
  return requestJson(
    includeDeleted
      ? '/api/decision-models?includeDeleted=true'
      : '/api/decision-models',
  )
}

export function createDecisionModel(
  payload: DecisionModelCreateInput,
): Promise<DecisionModelDefinition> {
  return requestJson('/api/decision-models', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function updateDecisionModel(
  modelId: string,
  payload: DecisionModelUpdateInput,
): Promise<DecisionModelDefinition> {
  return requestJson(`/api/decision-models/${modelId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function deleteDecisionModel(modelId: string): Promise<void> {
  await request(`/api/decision-models/${modelId}`, { method: 'DELETE' })
}

export function createConclusion(payload: ConclusionInput): Promise<ConclusionRecord> {
  return requestJson('/api/conclusions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function updateConclusion(
  id: number,
  payload: ConclusionUpdateInput,
): Promise<ConclusionRecord> {
  return requestJson(`/api/conclusions/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function deleteConclusion(id: number): Promise<void> {
  await request(`/api/conclusions/${id}`, { method: 'DELETE' })
}

export function listDecisions(query: string, status: DecisionStatus | '', offset: number) {
  const params = new URLSearchParams({ limit: '25', offset: String(offset) })
  if (query) params.set('query', query)
  if (status) params.set('status', status)
  return requestJson<{ count: number; offset: number; items: DecisionSummary[] }>(
    `/api/decisions?${params}`,
  )
}

export function getDecision(id: number): Promise<DecisionRecord> {
  return requestJson(`/api/decisions/${id}`)
}

export function createDecision(details: DecisionDetails): Promise<DecisionRecord> {
  return requestJson('/api/decisions', decisionRequest('POST', details))
}

export function updateDecision(
  id: number, expectedVersion: number, details: DecisionDetails,
): Promise<DecisionRecord> {
  return requestJson(`/api/decisions/${id}`, decisionRequest('PATCH', { ...details, expectedVersion }))
}

export function saveDecisionTree(
  id: number, expectedVersion: number, nodes: DecisionNode[],
): Promise<DecisionRecord> {
  return requestJson(`/api/decisions/${id}/tree`, decisionRequest('PATCH', { expectedVersion, nodes }))
}

export async function deleteDecision(id: number, expectedVersion: number): Promise<void> {
  await request(`/api/decisions/${id}?expectedVersion=${expectedVersion}`, { method: 'DELETE' })
}

function decisionRequest(method: 'POST' | 'PATCH', payload: object): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }
}
