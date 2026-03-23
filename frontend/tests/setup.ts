import { vi } from 'vitest'
import { config } from '@vue/test-utils'

// Mock Vue Router
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    go: vi.fn(),
    back: vi.fn(),
    forward: vi.fn()
  }),
  useRoute: () => ({
    params: {},
    query: {},
    path: '/',
    name: 'home'
  })
}))

// Mock Pinia stores
vi.mock('@stores/auth', () => ({
  useAuthStore: () => ({
    user: { id: '1', email: 'test@example.com', role: 'teacher' },
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn()
  })
}))

// Mock API
vi.mock('@services/gradingApi', () => ({
  default: {
    getCopy: vi.fn(),
    getCopies: vi.fn(),
    saveScores: vi.fn(),
    saveRemarks: vi.fn(),
    saveGlobalAppreciation: vi.fn(),
    getAnnotations: vi.fn(),
    createAnnotation: vi.fn(),
    updateAnnotation: vi.fn(),
    deleteAnnotation: vi.fn()
  }
}))

// Mock PDF.js
vi.mock('pdfjs-dist', () => ({
  getDocument: vi.fn(() => Promise.resolve({
    numPages: 5,
    getPage: vi.fn(() => Promise.resolve({
      getTextContent: vi.fn(() => Promise.resolve({ items: [] })),
      render: vi.fn(() => Promise.resolve())
    }))
  }))
}))

// Global test configuration
config.global.stubs = {
  'transition': false,
  'transition-group': false
}

// Mock window methods
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
vi.stubGlobal('localStorage', localStorageMock)

// Mock crypto
vi.stubGlobal('crypto', {
  randomUUID: vi.fn(() => 'test-uuid-' + Math.random().toString(36).substr(2, 9))
})
