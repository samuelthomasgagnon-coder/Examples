import '@testing-library/jest-dom'

// Polyfill minimal WebSocket for tests where hooks access it
class MockWebSocket {
  static OPEN = 1
  constructor() {
    this.readyState = 0
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      this.onopen && this.onopen()
    }, 0)
  }
  send() {}
  close() { this.readyState = 3; this.onclose && this.onclose() }
}

// Provide WebSocket, Image, URL mocks where missing
if (!global.WebSocket) global.WebSocket = MockWebSocket
// Ensure Image exists with onload/onerror hooks and default size
if (!global.Image) {
  global.Image = class {
    constructor() { this.width = 2; this.height = 2; }
    set src(v) { setTimeout(() => this.onload && this.onload()) }
  }
}
// Ensure URL object and blob helpers always exist
if (!global.URL) global.URL = {}
if (typeof global.URL.createObjectURL !== 'function') global.URL.createObjectURL = () => 'blob://test'
if (typeof global.URL.revokeObjectURL !== 'function') global.URL.revokeObjectURL = () => {}
