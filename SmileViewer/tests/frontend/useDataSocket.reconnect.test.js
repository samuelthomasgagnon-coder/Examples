import { renderHook, act, waitFor } from '@testing-library/react'
import useDataSocket from '../../FrontEnd/hooks/useDataSocket'

describe('useDataSocket reconnect/backoff', () => {
  it('connects and processes current_settings with immediate-open mock', async () => {
    const originalWS = global.WebSocket
    class ImmediateWS {
      static OPEN = 1
      constructor(url) {
        this.url = url
        this.readyState = 0
        setTimeout(() => {
          this.readyState = ImmediateWS.OPEN
          this.onopen && this.onopen()
          // after open, send current_settings synchronously
          const msg = JSON.stringify({ type: 'current_settings', settings: { DRAW_LANDMARKS: false, DRAW_FACE_BB: true, DRAW_SMILE_BB: true, DRAW_ROTATED_BB: false, RECORD: true } })
          this.onmessage && this.onmessage({ data: msg })
        }, 0)
      }
      send() {}
      close() { this.onclose && this.onclose() }
    }
    global.WebSocket = ImmediateWS

    const { result } = renderHook(() => useDataSocket('ws://localhost:8000/controls'))
    await waitFor(() => {
      expect(result.current.connected).toBe(true)
      expect(result.current.settings.RECORD).toBe(true)
      expect(result.current.settings.DRAW_LANDMARKS).toBe(false)
    }, { timeout: 1500 })

    global.WebSocket = originalWS
  })
})


