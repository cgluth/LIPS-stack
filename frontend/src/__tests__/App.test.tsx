import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import axios from 'axios'
import App from '../App'

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

vi.mock('axios')

vi.mock('@monaco-editor/react', () => ({
  default: (props: { value?: string; onChange?: (v: string) => void }) => (
    <textarea
      data-testid="monaco-editor"
      value={props.value ?? ''}
      onChange={(e) => props.onChange?.(e.target.value)}
    />
  ),
}))

vi.mock('react-resizable-panels', () => ({
  Panel: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  PanelGroup: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  PanelResizeHandle: () => <div />,
}))

// ---------------------------------------------------------------------------
// beforeEach — wire up axios.get defaults
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.mocked(axios.get).mockImplementation((url: string) => {
    if (url === '/api/templates') {
      return Promise.resolve({ data: { templates: ['newtonian-3d-pipeline'] } })
    }
    if (url === '/api/workspaces') {
      return Promise.resolve({ data: { workspaces: [] } })
    }
    if (url === '/api/config/apikey') {
      return Promise.resolve({ data: { set: false, masked: '' } })
    }
    return Promise.resolve({ data: {} })
  })
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('App welcome screen', () => {
  it('renders LIPS IDE heading on welcome screen', async () => {
    render(<App />)
    const heading = await screen.findByRole('heading', { name: /LIPS IDE/i })
    expect(heading).toBeInTheDocument()
  })

  it('renders subtitle text', async () => {
    render(<App />)
    const subtitle = await screen.findByText(/LLM-driven/i)
    expect(subtitle).toBeInTheDocument()
  })

  it('renders New Project button', async () => {
    render(<App />)
    const btn = await screen.findByText(/\+ New Project/i)
    expect(btn).toBeInTheDocument()
  })

  it('renders feature badges', async () => {
    render(<App />)
    expect(await screen.findByText('Write')).toBeInTheDocument()
    expect(await screen.findByText('Generate')).toBeInTheDocument()
    expect(await screen.findByText('Visualize')).toBeInTheDocument()
  })

  it('shows api key button with Set API Key text when key not set', async () => {
    render(<App />)
    expect(await screen.findByText(/Set API Key/i)).toBeInTheDocument()
  })

  it('shows api key as set when API returns set=true', async () => {
    vi.mocked(axios.get).mockImplementation((url: string) => {
      if (url === '/api/templates') {
        return Promise.resolve({ data: { templates: ['newtonian-3d-pipeline'] } })
      }
      if (url === '/api/workspaces') {
        return Promise.resolve({ data: { workspaces: [] } })
      }
      if (url === '/api/config/apikey') {
        return Promise.resolve({ data: { set: true, masked: 'sk-abc…xyz' } })
      }
      return Promise.resolve({ data: {} })
    })

    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('sk-abc…xyz')).toBeInTheDocument()
    })
  })

  it('opens new project modal on button click', async () => {
    render(<App />)
    const btn = await screen.findByText(/\+ New Project/i)
    fireEvent.click(btn)
    expect(await screen.findByRole('heading', { name: /New Project/i })).toBeInTheDocument()
  })
})
