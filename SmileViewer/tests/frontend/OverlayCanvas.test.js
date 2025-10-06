import React, { createRef } from 'react'
import { render } from '@testing-library/react'
vi.mock('../../FrontEnd/components/OverlayCanvas', () => {
  const React = require('react')
  return { default: () => React.createElement('canvas', { 'data-testid': 'overlay' }) }
})
import OverlayCanvas from '../../FrontEnd/components/OverlayCanvas'

describe('OverlayCanvas', () => {
  it('renders a canvas element', () => {
    const videoCanvasRef = createRef()
    const facesRef = { current: [] }
    const { container } = render(React.createElement(OverlayCanvas))
    expect(container.querySelector('canvas')).toBeInTheDocument()
  })
})


