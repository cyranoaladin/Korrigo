import { describe, expect, it } from 'vitest'
import { normalizeCollectionResponse } from '@utils/normalizeCollection'

describe('normalizeCollectionResponse', () => {
  it('returns flat arrays unchanged', () => {
    const data = [{ id: 'a' }, { id: 'b' }]

    expect(normalizeCollectionResponse(data)).toEqual(data)
  })

  it('extracts results from DRF paginated responses', () => {
    const data = {
      count: 2,
      next: null,
      previous: null,
      results: [{ id: 'a' }, { id: 'b' }],
    }

    expect(normalizeCollectionResponse(data)).toEqual(data.results)
  })

  it('returns an empty array for non-collection payloads', () => {
    expect(normalizeCollectionResponse({ detail: 'forbidden' })).toEqual([])
    expect(normalizeCollectionResponse(null)).toEqual([])
  })
})
