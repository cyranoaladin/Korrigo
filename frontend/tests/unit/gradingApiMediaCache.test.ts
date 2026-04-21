import { beforeEach, describe, expect, it, vi } from 'vitest'

const loadGradingApi = async () => {
  const module = await vi.importActual('../../src/services/gradingApi')
  return module.default
}

const loadApi = async () => {
  const module = await vi.importActual('../../src/services/api')
  return module.default
}

describe('gradingApi media cache helpers', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('appends a cache-busting version to protected media URLs', async () => {
    const gradingApi = await loadGradingApi()

    expect(gradingApi.getMediaUrl('copies/pages/page_001.png', { version: 1713700000000 }))
      .toBe('/api/media/copies/pages/page_001.png?v=1713700000000')
  })

  it('preserves existing query params when appending a version', async () => {
    const gradingApi = await loadGradingApi()

    expect(gradingApi.getMediaUrl('copies/pages/page_001.png?download=1', { version: 'fresh' }))
      .toBe('/api/media/copies/pages/page_001.png?download=1&v=fresh')
  })

  it('keeps rooted API paths unchanged when resolving PDF URLs', async () => {
    const gradingApi = await loadGradingApi()
    const api = await loadApi()

    api.defaults.baseURL = '/api'

    expect(gradingApi.resolveUrl('/api/media/copies/source/new.pdf'))
      .toBe('/api/media/copies/source/new.pdf')
  })

  it('prefixes non-rooted API paths with the axios base URL', async () => {
    const gradingApi = await loadGradingApi()
    const api = await loadApi()

    api.defaults.baseURL = '/api'

    expect(gradingApi.resolveUrl('grading/copies/abc/final-pdf/'))
      .toBe('/api/grading/copies/abc/final-pdf/')
  })
})
