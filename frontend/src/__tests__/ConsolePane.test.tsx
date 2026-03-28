import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ConsolePane from '../components/ConsolePane'
import type { ConsoleLine } from '../App'

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ConsolePane', () => {
  it('shows empty state when no lines', () => {
    render(<ConsolePane lines={[]} onClear={vi.fn()} />)
    expect(screen.getByText(/Run a pipeline stage/i)).toBeInTheDocument()
  })

  it('renders line text content', () => {
    const lines: ConsoleLine[] = [{ type: 'stdout', text: 'Hello world output' }]
    render(<ConsolePane lines={lines} onClear={vi.fn()} />)
    expect(screen.getByText('Hello world output')).toBeInTheDocument()
  })

  it('renders success line', () => {
    const lines: ConsoleLine[] = [{ type: 'success', text: 'Done!' }]
    render(<ConsolePane lines={lines} onClear={vi.fn()} />)
    expect(screen.getByText('Done!')).toBeInTheDocument()
  })

  it('renders error line', () => {
    const lines: ConsoleLine[] = [{ type: 'error', text: 'Failed!' }]
    render(<ConsolePane lines={lines} onClear={vi.fn()} />)
    expect(screen.getByText('Failed!')).toBeInTheDocument()
  })

  it('renders info line', () => {
    const lines: ConsoleLine[] = [{ type: 'info', text: 'Starting...' }]
    render(<ConsolePane lines={lines} onClear={vi.fn()} />)
    expect(screen.getByText('Starting...')).toBeInTheDocument()
  })

  it('renders multiple lines', () => {
    const lines: ConsoleLine[] = [
      { type: 'info', text: 'Line one' },
      { type: 'stdout', text: 'Line two' },
      { type: 'success', text: 'Line three' },
    ]
    render(<ConsolePane lines={lines} onClear={vi.fn()} />)
    expect(screen.getByText('Line one')).toBeInTheDocument()
    expect(screen.getByText('Line two')).toBeInTheDocument()
    expect(screen.getByText('Line three')).toBeInTheDocument()
  })

  it('clear button is visible', () => {
    render(<ConsolePane lines={[]} onClear={vi.fn()} />)
    expect(screen.getByRole('button', { name: /clear/i })).toBeInTheDocument()
  })

  it('clear button calls onClear callback', async () => {
    const user = userEvent.setup()
    const onClear = vi.fn()
    render(<ConsolePane lines={[]} onClear={onClear} />)
    const clearBtn = screen.getByRole('button', { name: /clear/i })
    await user.click(clearBtn)
    expect(onClear).toHaveBeenCalledTimes(1)
  })

  it('does not show empty state when lines exist', () => {
    const lines: ConsoleLine[] = [{ type: 'stdout', text: 'Some output' }]
    render(<ConsolePane lines={lines} onClear={vi.fn()} />)
    expect(screen.queryByText(/Run a pipeline stage/i)).not.toBeInTheDocument()
  })
})
