import type {
  ConclusionInput,
  ConclusionListResponse,
  ConclusionRecord,
  ConclusionUpdateInput,
  DecisionModelListResponse,
} from './types'

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

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, init)
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const message =
      response.status === 404
        ? '没有找到这条结论'
        : response.status === 409
          ? '这条结论已经被其他写入者更新'
          : '请求没有成功，请稍后重试'
    throw new ApiError(message, response.status, body)
  }
  return response.json() as Promise<T>
}

export function listConclusions(limit = 100): Promise<ConclusionListResponse> {
  return requestJson(`/api/conclusions?limit=${limit}`)
}

export function getConclusion(id: number): Promise<ConclusionRecord> {
  return requestJson(`/api/conclusions/${id}`)
}

export function listDecisionModels(): Promise<DecisionModelListResponse> {
  return requestJson('/api/decision-models')
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
