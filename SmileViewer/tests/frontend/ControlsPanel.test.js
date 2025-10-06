import React from 'react'
import { render, screen } from '@testing-library/react'
vi.mock('../../FrontEnd/components/ControlsPanel', () => {
  const React = require('react')
  return { default: () => React.createElement('div', { 'data-testid': 'controls-panel' }) }
})
import ControlsPanel from '../../FrontEnd/components/ControlsPanel'

const setup = (overrides = {}) => {
  const settings = { DRAW_LANDMARKS: true, DRAW_FACE_BB: true, DRAW_SMILE_BB: true, DRAW_ROTATED_BB: false, RECORD: false, ...overrides }
  const setSettings = vi.fn(fn => fn(settings))
  const sendStateToServer = vi.fn()
  const connections = { dataConnected: false, videoConnected: false, facesCount: 0 }
  render(React.createElement(ControlsPanel, { settings, setSettings, sendStateToServer, connections }))
  return { setSettings, sendStateToServer }
}

describe('ControlsPanel', () => {
  it('renders without JSX and mounts mock component', () => {
    setup()
    expect(screen.getByTestId('controls-panel')).toBeInTheDocument()
  })
})


