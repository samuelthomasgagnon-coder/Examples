import { renderHook } from '@testing-library/react'
import { createRef } from 'react'
import useVideoSocket from '../../FrontEnd/hooks/useVideoSocket'

describe('useVideoSocket', () => {
  it('returns video connection state and ws ref', () => {
    const canvasRef = createRef()
    const { result } = renderHook(() => useVideoSocket('ws://localhost:8000/controls', canvasRef))
    expect(result.current).toHaveProperty('videoWs')
    expect(result.current).toHaveProperty('videoConnected')
  })
})


