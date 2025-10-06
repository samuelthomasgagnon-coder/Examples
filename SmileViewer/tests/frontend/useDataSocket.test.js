import { renderHook, act } from '@testing-library/react'
import useDataSocket from '../../FrontEnd/hooks/useDataSocket'

describe('useDataSocket', () => {
  it('initializes with default settings and disconnected state', () => {
    const { result } = renderHook(() => useDataSocket('ws://localhost:8000/controls'))
    const { connected, settings, facesRef, facesTick } = result.current
    expect(connected).toBe(false)
    expect(settings).toMatchObject({
      DRAW_LANDMARKS: false,
      DRAW_FACE_BB: false,
      DRAW_SMILE_BB: true,
      DRAW_ROTATED_BB: false,
      RECORD: false,
    })
    expect(Array.isArray(facesRef.current)).toBe(true)
    expect(typeof facesTick).toBe('number')
  })

  it('sendStateToServer returns false when socket not open', () => {
    const { result } = renderHook(() => useDataSocket('ws://localhost:8000/controls'))
    const ok = result.current.sendStateToServer('DRAW_FACE_BB', true)
    expect(ok).toBe(false)
  })
})


