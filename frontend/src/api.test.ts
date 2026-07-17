import { afterEach, describe, expect, it, vi } from 'vitest'
import { deleteConclusion } from './api'

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
})
