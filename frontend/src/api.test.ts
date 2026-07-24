import { afterEach, describe, expect, it, vi } from 'vitest'
import { deleteConclusion, updateDecisionModel } from './api'

describe('Conclusion API', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('deletes a conclusion without trying to parse the empty 204 response', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(deleteConclusion(42)).resolves.toBeUndefined()
    expect(fetchMock).toHaveBeenCalledWith('/api/conclusions/42', {
      method: 'DELETE',
    })
  })

  it('updates a decision model with optimistic version checking', async () => {
    const responseBody = {
      id: 'constraint-check',
      version: 2,
      name: '关键约束检查',
      explanation: '检查真正限制结果的硬约束。',
      isBuiltin: false,
      createdAt: '2026-07-24T00:00:00Z',
      updatedAt: '2026-07-24T00:00:00Z',
    }
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responseBody), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      updateDecisionModel('constraint-check', {
        name: '关键约束检查',
        explanation: '检查真正限制结果的硬约束。',
        expectedVersion: 1,
      }),
    ).resolves.toEqual(responseBody)
    expect(fetchMock).toHaveBeenCalledWith('/api/decision-models/constraint-check', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: '关键约束检查',
        explanation: '检查真正限制结果的硬约束。',
        expectedVersion: 1,
      }),
    })
  })
})
