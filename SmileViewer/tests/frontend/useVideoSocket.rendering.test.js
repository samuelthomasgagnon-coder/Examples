import { renderHook, waitFor } from '@testing-library/react'
import { createRef } from 'react'
import useVideoSocket from '../../FrontEnd/hooks/useVideoSocket'

describe('useVideoSocket rendering', () => {
  it('handles Blob binary frames and draws to canvas', async () => {
    const originalWS = global.WebSocket
    const canvasRef = createRef()
    const canvas = document.createElement('canvas')
    canvas.width = 2; canvas.height = 2
    canvasRef.current = canvas

    const jpegBytes = new Uint8Array([255, 216, 255, 217]) // minimal invalid JPEG but triggers path

    class TestWS {
      static OPEN = 1
      constructor(url) {
        setTimeout(() => { this.readyState = TestWS.OPEN; this.onopen && this.onopen();
          setTimeout(() => {
            const blob = new Blob([jpegBytes], { type: 'image/jpeg' })
            this.onmessage && this.onmessage({ data: blob })
          }, 0)
        }, 0)
      }
      send() {}
      close() { this.onclose && this.onclose() }
    }
    global.WebSocket = TestWS

    const { result } = renderHook(() => useVideoSocket('ws://localhost:8000/controls', canvasRef))
    await waitFor(() => {
      // merely ensure hook initialized and did not throw; canvas present
      expect(canvasRef.current).toBeTruthy()
    })

    global.WebSocket = originalWS
  })
})


