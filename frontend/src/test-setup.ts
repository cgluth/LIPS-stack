import '@testing-library/jest-dom'

// Mock ResizeObserver which is not available in jsdom
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Mock scrollIntoView which is not implemented in jsdom
window.HTMLElement.prototype.scrollIntoView = vi.fn()

// Mock WebSocket
global.WebSocket = vi.fn().mockImplementation(() => ({
  onmessage: null,
  onerror: null,
  onclose: null,
  close: vi.fn(),
  send: vi.fn(),
})) as unknown as typeof WebSocket
