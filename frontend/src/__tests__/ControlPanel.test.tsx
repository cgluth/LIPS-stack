import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ControlPanel from '../components/ControlPanel'
import type { Stage } from '../App'

// ---------------------------------------------------------------------------
// Default props factory
// ---------------------------------------------------------------------------

const defaultStages: Stage[] = [
  { name: 'requirements', has_output: false },
  { name: 'specifications', has_output: false },
  { name: 'code-raw', has_output: false },
]

const defaultProps = {
  stages: defaultStages,
  runningStage: null as string | null,
  isVisualizing: false,
  requirementsEmpty: false,
  onRunStage: vi.fn(),
  onVisualize: vi.fn(),
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ControlPanel', () => {
  it('renders all stage names', () => {
    render(<ControlPanel {...defaultProps} />)
    expect(screen.getByText('requirements')).toBeInTheDocument()
    expect(screen.getByText('specifications')).toBeInTheDocument()
    expect(screen.getByText('code-raw')).toBeInTheDocument()
  })

  it('all stage buttons disabled when requirementsEmpty is true', () => {
    render(<ControlPanel {...defaultProps} requirementsEmpty={true} />)
    const buttons = screen
      .getAllByRole('button')
      .filter((b) => ['requirements', 'specifications', 'code-raw'].some((n) => b.textContent?.includes(n)))
    expect(buttons.length).toBeGreaterThan(0)
    buttons.forEach((btn) => {
      expect(btn).toBeDisabled()
    })
  })

  it('shows warning banner when requirementsEmpty', () => {
    render(<ControlPanel {...defaultProps} requirementsEmpty={true} />)
    expect(screen.getByText(/Write your prompt first/i)).toBeInTheDocument()
  })

  it('first stage enabled when requirements not empty and no busy', () => {
    render(<ControlPanel {...defaultProps} requirementsEmpty={false} runningStage={null} />)
    // The first stage button (requirements) should NOT be disabled
    const requirementsButton = screen
      .getAllByRole('button')
      .find((b) => b.textContent?.includes('requirements'))
    expect(requirementsButton).toBeDefined()
    expect(requirementsButton).not.toBeDisabled()
  })

  it('second stage disabled when first has no output', () => {
    const stages: Stage[] = [
      { name: 'requirements', has_output: false },
      { name: 'specifications', has_output: false },
      { name: 'code-raw', has_output: false },
    ]
    render(<ControlPanel {...defaultProps} stages={stages} requirementsEmpty={false} />)
    const specsButton = screen
      .getAllByRole('button')
      .find((b) => b.textContent?.includes('specifications'))
    expect(specsButton).toBeDefined()
    expect(specsButton).toBeDisabled()
  })

  it('second stage enabled when first has output', () => {
    const stages: Stage[] = [
      { name: 'requirements', has_output: true },
      { name: 'specifications', has_output: false },
      { name: 'code-raw', has_output: false },
    ]
    render(<ControlPanel {...defaultProps} stages={stages} requirementsEmpty={false} />)
    const specsButton = screen
      .getAllByRole('button')
      .find((b) => b.textContent?.includes('specifications'))
    expect(specsButton).toBeDefined()
    expect(specsButton).not.toBeDisabled()
  })

  it('running stage shows spinner (button is disabled)', () => {
    render(
      <ControlPanel {...defaultProps} runningStage="requirements" requirementsEmpty={false} />
    )
    const requirementsButton = screen
      .getAllByRole('button')
      .find((b) => b.textContent?.includes('requirements'))
    expect(requirementsButton).toBeDefined()
    // When running, canRun is false so button is disabled
    expect(requirementsButton).toBeDisabled()
  })

  it('visualize button disabled when busy', () => {
    render(
      <ControlPanel {...defaultProps} runningStage="requirements" requirementsEmpty={false} />
    )
    const visualizeButton = screen.getByRole('button', { name: /Visualize/i })
    expect(visualizeButton).toBeDisabled()
  })

  it('visualize button calls onVisualize when clicked', async () => {
    const user = userEvent.setup()
    const onVisualize = vi.fn()
    // Make all stages have output so blocked=false
    const stages: Stage[] = [
      { name: 'requirements', has_output: true },
      { name: 'specifications', has_output: true },
      { name: 'code-raw', has_output: true },
    ]
    render(
      <ControlPanel
        {...defaultProps}
        stages={stages}
        onVisualize={onVisualize}
        requirementsEmpty={false}
        runningStage={null}
        isVisualizing={false}
      />
    )
    const visualizeButton = screen.getByRole('button', { name: /Visualize/i })
    await user.click(visualizeButton)
    expect(onVisualize).toHaveBeenCalledTimes(1)
  })

  it('visualize button shows Visualizing text when isVisualizing', () => {
    render(
      <ControlPanel {...defaultProps} isVisualizing={true} requirementsEmpty={false} />
    )
    expect(screen.getByText(/Visualizing/i)).toBeInTheDocument()
  })
})
