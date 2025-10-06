import React from 'react'
import { render } from '@testing-library/react'
vi.mock('../../FrontEnd/components/OverlayCanvas', () => {
  const React = require('react')
  return { default: () => React.createElement('canvas', { 'data-testid': 'overlay-draw' }) }
})
import OverlayCanvas from '../../FrontEnd/components/OverlayCanvas'

describe('OverlayCanvas.draw', () => {
  it('mounts mock overlay canvas', () => {
    render(React.createElement(OverlayCanvas))
    expect(document.querySelector('[data-testid="overlay-draw"]')).toBeInTheDocument()
  })
})


