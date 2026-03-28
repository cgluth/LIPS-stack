import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import VisualizerPane from '../components/VisualizerPane'
import type { VizResult } from '../App'

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('VisualizerPane', () => {
  it('shows empty state when no result and not loading', () => {
    render(<VisualizerPane result={null} isLoading={false} />)
    expect(screen.getByText(/No visualization yet/i)).toBeInTheDocument()
  })

  it('shows loading state when isLoading is true', () => {
    render(<VisualizerPane result={null} isLoading={true} />)
    expect(screen.getByText(/Generating visualization/i)).toBeInTheDocument()
    expect(screen.queryByText(/No visualization yet/i)).not.toBeInTheDocument()
  })

  it('renders iframe with srcDoc for HTML result', () => {
    const htmlContent = '<html>test</html>'
    const result: VizResult = { type: 'html', data: htmlContent, script: '' }
    render(<VisualizerPane result={result} isLoading={false} />)
    const iframe = screen.getByTitle('Simulation visualization') as HTMLIFrameElement
    expect(iframe).toBeInTheDocument()
    expect(iframe.getAttribute('srcdoc') ?? iframe.getAttribute('srcDoc')).toBe(htmlContent)
  })

  it('does not render iframe when loading', () => {
    const result: VizResult = { type: 'html', data: '<html>test</html>', script: '' }
    render(<VisualizerPane result={result} isLoading={true} />)
    expect(screen.queryByTitle('Simulation visualization')).not.toBeInTheDocument()
  })

  it('shows error UI when result has error', () => {
    const result: VizResult = { error: 'LLM failed', script: '' }
    render(<VisualizerPane result={result} isLoading={false} />)
    expect(screen.getByText('Visualization failed')).toBeInTheDocument()
    expect(screen.getByText('LLM failed')).toBeInTheDocument()
  })

  it('shows live badge for successful HTML result', () => {
    const result: VizResult = { type: 'html', data: '<html>test</html>', script: '' }
    render(<VisualizerPane result={result} isLoading={false} />)
    expect(screen.getByText('live')).toBeInTheDocument()
  })

  it('show script button visible when script exists', () => {
    const result: VizResult = { type: 'html', data: '<html>test</html>', script: 'console.log("hi")' }
    render(<VisualizerPane result={result} isLoading={false} />)
    expect(screen.getByRole('button', { name: /Show Script/i })).toBeInTheDocument()
  })

  it('show script button toggles to show script content', async () => {
    const user = userEvent.setup()
    const scriptContent = 'console.log("hi")'
    const result: VizResult = { type: 'html', data: '<html>test</html>', script: scriptContent }
    render(<VisualizerPane result={result} isLoading={false} />)

    const showScriptBtn = screen.getByRole('button', { name: /Show Script/i })
    await user.click(showScriptBtn)

    const pre = screen.getByText(scriptContent)
    expect(pre.tagName.toLowerCase()).toBe('pre')
  })

  it('show script button toggles back to output', async () => {
    const user = userEvent.setup()
    const result: VizResult = {
      type: 'html',
      data: '<html>test</html>',
      script: 'console.log("hi")',
    }
    render(<VisualizerPane result={result} isLoading={false} />)

    // First click — show script
    const showScriptBtn = screen.getByRole('button', { name: /Show Script/i })
    await user.click(showScriptBtn)

    // Button should now say "Show Output"
    expect(screen.getByRole('button', { name: /Show Output/i })).toBeInTheDocument()

    // Click again — back to output (iframe)
    const showOutputBtn = screen.getByRole('button', { name: /Show Output/i })
    await user.click(showOutputBtn)

    expect(screen.getByTitle('Simulation visualization')).toBeInTheDocument()
  })
})
