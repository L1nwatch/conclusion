import type { ConclusionListResponse, ConclusionRecord } from './types'

const apiBase = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '')

async function readJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBase}${path}`)
  if (!response.ok) {
    const message = response.status === 404 ? '没有找到这条结论' : '暂时无法读取结论'
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export function listConclusions(limit = 100): Promise<ConclusionListResponse> {
  return readJson(`/api/conclusions?limit=${limit}`)
}

export function getConclusion(id: number): Promise<ConclusionRecord> {
  return readJson(`/api/conclusions/${id}`)
}

