import { useState, useEffect, useCallback, useRef } from 'react'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import axios from 'axios'
import ApiKeyModal from './components/ApiKeyModal'

import EditorPane from './components/EditorPane'
import ControlPanel from './components/ControlPanel'
import ConsolePane from './components/ConsolePane'
import VisualizerPane from './components/VisualizerPane'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Stage {
  name: string
  has_output: boolean
}

export interface ConsoleLine {
  type: 'info' | 'stdout' | 'success' | 'error' | 'system'
  text: string
}

export type VizResult =
  | { type: 'image'; data: string; script: string }
  | { type: 'html'; data: string; script: string }
  | { error: string; script?: string }

// ---------------------------------------------------------------------------
// New-project modal
// ---------------------------------------------------------------------------

interface NewProjectModalProps {
  templates: string[]
  onClose: () => void
  onCreate: (template: string, name: string) => Promise<void>
}

function NewProjectModal({ templates, onClose, onCreate }: NewProjectModalProps) {
  const [template, setTemplate] = useState(templates[0] ?? '')
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) { setErr('Name is required.'); return }
    if (!template) { setErr('Select a template.'); return }
    setBusy(true)
    setErr('')
    try {
      await onCreate(template, name.trim())
      onClose()
    } catch (ex: unknown) {
      const msg = axios.isAxiosError(ex)
        ? (ex.response?.data?.detail ?? ex.message)
        : String(ex)
      setErr(msg)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50"
         style={{ background: 'rgba(0,0,0,0.8)' }}>
      <form
        onSubmit={handleSubmit}
        className="rounded-2xl p-7 w-[440px]"
        style={{
          background: '#161616',
          border: '1px solid #2a2a2a',
          boxShadow: '0 20px 60px rgba(0,0,0,0.7), 0 8px 24px rgba(0,0,0,0.5)',
        }}
      >
        {/* Title */}
        <div className="mb-7">
          <h2 className="text-ide-text font-bold text-lg tracking-tight">New Project</h2>
          <p className="text-ide-muted text-xs mt-1.5">Create a workspace from a physics simulation template</p>
        </div>

        {/* Template */}
        <label className="block text-ide-muted text-[11px] font-semibold uppercase tracking-widest mb-2">
          Template
        </label>
        <select
          className="w-full bg-ide-bg border border-ide-border text-ide-text rounded-xl px-3 py-2.5 mb-5 text-xs focus:outline-none focus:border-ide-accent transition-colors font-sans"
          value={template}
          onChange={e => setTemplate(e.target.value)}
        >
          {templates.map(t => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>

        {/* Name */}
        <label className="block text-ide-muted text-[11px] font-semibold uppercase tracking-widest mb-2">
          Project name
        </label>
        <input
          type="text"
          placeholder="e.g. lorenz-chaos"
          className="w-full bg-ide-bg border border-ide-border text-ide-text rounded-xl px-3 py-2.5 mb-5 text-xs focus:outline-none focus:border-ide-accent transition-colors placeholder-ide-faint font-mono"
          value={name}
          onChange={e => setName(e.target.value)}
        />

        {err && (
          <div className="mb-5 px-3 py-2.5 rounded-xl bg-ide-error/10 border border-ide-error/30 text-ide-error text-xs">
            {err}
          </div>
        )}

        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={onClose}
            className="btn-ghost px-4 py-2 text-xs rounded-xl font-medium"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={busy}
            className="btn-accent px-5 py-2 text-xs rounded-xl font-semibold"
          >
            {busy ? 'Creating…' : 'Create Project'}
          </button>
        </div>
      </form>
    </div>
  )
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

export default function App() {
  const [templates, setTemplates] = useState<string[]>([])
  const [workspaces, setWorkspaces] = useState<string[]>([])
  const [activeWorkspace, setActiveWorkspace] = useState<string | null>(null)
  const [showNewProject, setShowNewProject] = useState(false)
  const [showApiKey, setShowApiKey] = useState(false)
  const [apiKeySet, setApiKeySet] = useState(false)
  const [apiKeyMasked, setApiKeyMasked] = useState('')

  const [stages, setStages] = useState<Stage[]>([])
  const [requirementsEmpty, setRequirementsEmpty] = useState(true)
  const [runningStage, setRunningStage] = useState<string | null>(null)

  const [activeFile, setActiveFile] = useState('requirements/contents/product-requirements.md')
  const [fileContent, setFileContent] = useState('')
  const [isDirty, setIsDirty] = useState(false)
  const [fileList, setFileList] = useState<string[]>([])

  const [consoleLines, setConsoleLines] = useState<ConsoleLine[]>([])
  const consoleRef = useRef<ConsoleLine[]>([])

  const [vizResult, setVizResult] = useState<VizResult | null>(null)
  const [isVisualizing, setIsVisualizing] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)

  // ---------------------------------------------------------------------------
  // Loaders
  // ---------------------------------------------------------------------------

  const loadApiKeyStatus = useCallback(async () => {
    const res = await axios.get<{ set: boolean; masked: string }>('/api/config/apikey')
    setApiKeySet(res.data.set)
    setApiKeyMasked(res.data.masked)
  }, [])

  const loadMeta = useCallback(async () => {
    const [tRes, wRes] = await Promise.all([
      axios.get<{ templates: string[] }>('/api/templates'),
      axios.get<{ workspaces: string[] }>('/api/workspaces'),
    ])
    setTemplates(tRes.data.templates)
    setWorkspaces(wRes.data.workspaces)
  }, [])

  useEffect(() => { loadMeta(); loadApiKeyStatus() }, [loadMeta, loadApiKeyStatus])

  const loadStages = useCallback(async (wsId: string) => {
    const res = await axios.get<{ stages: Stage[]; requirements_empty: boolean }>(
      `/api/workspaces/${wsId}/stages`
    )
    setStages(res.data.stages)
    setRequirementsEmpty(res.data.requirements_empty)
  }, [])

  const loadFileList = useCallback(async (wsId: string) => {
    const res = await axios.get<{ files: string[] }>(`/api/workspaces/${wsId}/files`)
    setFileList(res.data.files)
  }, [])

  const loadFile = useCallback(async (wsId: string, path: string) => {
    const res = await axios.get<{ content: string; exists: boolean }>(
      `/api/workspaces/${wsId}/file`,
      { params: { path } }
    )
    setFileContent(res.data.content)
    setIsDirty(false)
  }, [])

  useEffect(() => {
    if (!activeWorkspace) return
    loadStages(activeWorkspace)
    loadFileList(activeWorkspace)
    loadFile(activeWorkspace, activeFile)
  }, [activeWorkspace]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!activeWorkspace) return
    loadFile(activeWorkspace, activeFile)
  }, [activeFile]) // eslint-disable-line react-hooks/exhaustive-deps

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function appendConsole(lines: ConsoleLine[]) {
    consoleRef.current = [...consoleRef.current, ...lines]
    setConsoleLines([...consoleRef.current])
  }

  function clearConsole() {
    consoleRef.current = []
    setConsoleLines([])
  }

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  async function handleCreateWorkspace(template: string, name: string) {
    await axios.post('/api/workspaces', { template, name })
    await loadMeta()
    setActiveWorkspace(name)
    setActiveFile('requirements/contents/product-requirements.md')
    clearConsole()
    setVizResult(null)
  }

  async function handleSelectWorkspace(wsId: string) {
    setActiveWorkspace(wsId)
    setActiveFile('requirements/contents/product-requirements.md')
    clearConsole()
    setVizResult(null)
  }

  async function handleSaveFile() {
    if (!activeWorkspace) return
    await axios.post(`/api/workspaces/${activeWorkspace}/file`, {
      path: activeFile,
      content: fileContent,
    })
    setIsDirty(false)
    appendConsole([{ type: 'system', text: `✓ Saved ${activeFile}\n` }])
    loadStages(activeWorkspace)
  }

  function handleEditorChange(value: string | undefined) {
    setFileContent(value ?? '')
    setIsDirty(true)
  }

  async function handleRunStage(stage: string) {
    if (!activeWorkspace || runningStage) return
    if (isDirty) await handleSaveFile()

    clearConsole()
    setRunningStage(stage)
    wsRef.current?.close()

    const ws = new WebSocket(`ws://localhost:8000/ws/${activeWorkspace}/run/${stage}`)
    wsRef.current = ws

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data) as { type: string; data: string | number }
        if (msg.type === 'done') {
          setRunningStage(null)
          loadStages(activeWorkspace)
          loadFileList(activeWorkspace)
          loadFile(activeWorkspace, activeFile)
          ws.close()
        } else {
          appendConsole([{ type: msg.type as ConsoleLine['type'], text: String(msg.data) }])
        }
      } catch {
        appendConsole([{ type: 'stdout', text: evt.data }])
      }
    }
    ws.onerror = () => {
      appendConsole([{ type: 'error', text: 'WebSocket connection error.\n' }])
      setRunningStage(null)
    }
    ws.onclose = () => {
      if (runningStage === stage) setRunningStage(null)
    }
  }

  async function handleVisualize() {
    if (!activeWorkspace || isVisualizing) return
    setIsVisualizing(true)
    setVizResult(null)
    appendConsole([{ type: 'info', text: 'Running visualization pipeline…\n' }])
    try {
      const res = await axios.post<VizResult>(`/api/workspaces/${activeWorkspace}/visualize`)
      setVizResult(res.data)
      if ('error' in res.data) {
        appendConsole([{ type: 'error', text: `Visualization error: ${res.data.error}\n` }])
      } else {
        appendConsole([{ type: 'success', text: '✓ Visualization complete.\n' }])
      }
    } catch (ex: unknown) {
      const msg = axios.isAxiosError(ex) ? (ex.response?.data?.detail ?? ex.message) : String(ex)
      appendConsole([{ type: 'error', text: `Visualization failed: ${msg}\n` }])
    } finally {
      setIsVisualizing(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="h-screen flex flex-col bg-ide-bg overflow-hidden">

      {/* ── Header ──────────────────────────────────────────── */}
      <header className="flex items-center gap-4 px-5 py-3 shrink-0"
              style={{
                background: '#111111',
                borderBottom: '1px solid #222222',
              }}>

        {/* Logo */}
        <div className="flex items-baseline gap-2 shrink-0">
          <span className="text-ide-text font-black text-base tracking-widest">LIPS</span>
          <span className="text-ide-faint text-xs font-medium tracking-wider">IDE</span>
        </div>

        <div className="w-px h-4" style={{ background: '#2a2a2a' }} />

        {/* Workspace selector */}
        <select
          className="bg-ide-surface border border-ide-border text-ide-text text-xs rounded-xl px-3 py-1.5 focus:outline-none focus:border-ide-accent transition-colors max-w-[220px] font-sans"
          value={activeWorkspace ?? ''}
          onChange={e => e.target.value && handleSelectWorkspace(e.target.value)}
        >
          <option value="">— open a project —</option>
          {workspaces.map(w => (
            <option key={w} value={w}>{w}</option>
          ))}
        </select>

        <button
          onClick={() => setShowNewProject(true)}
          className="btn-accent text-xs px-4 py-1.5 rounded-xl font-semibold shrink-0"
        >
          + New
        </button>

        {/* Right side */}
        <div className="ml-auto flex items-center gap-3">
          {activeWorkspace && (
            <span className="text-ide-faint text-xs truncate max-w-[160px]">
              {activeWorkspace}
            </span>
          )}
          <button
            onClick={() => setShowApiKey(true)}
            title="API Key Settings"
            className={`text-xs px-3 py-1.5 rounded-xl border flex items-center gap-1.5 transition-colors font-medium ${
              apiKeySet
                ? 'border-ide-success/40 text-ide-success hover:border-ide-success hover:bg-ide-success/5'
                : 'border-ide-error/50 text-ide-error hover:border-ide-error animate-pulse'
            }`}
          >
            <span>{apiKeySet ? '●' : '○'}</span>
            <span>{apiKeySet ? apiKeyMasked : 'Set API Key'}</span>
          </button>
        </div>
      </header>

      {/* ── Main layout ─────────────────────────────────────── */}
      {activeWorkspace ? (
        <PanelGroup direction="vertical" className="flex-1 min-h-0">

          {/* Top row */}
          <Panel defaultSize={62} minSize={25}>
            <PanelGroup direction="horizontal" className="h-full">

              <Panel defaultSize={42} minSize={20}>
                <EditorPane
                  workspace={activeWorkspace}
                  fileList={fileList}
                  activeFile={activeFile}
                  content={fileContent}
                  isDirty={isDirty}
                  onChange={handleEditorChange}
                  onSave={handleSaveFile}
                  onSelectFile={setActiveFile}
                />
              </Panel>

              <PanelResizeHandle className="w-px" />

              <Panel defaultSize={16} minSize={14}>
                <ControlPanel
                  stages={stages}
                  runningStage={runningStage}
                  isVisualizing={isVisualizing}
                  requirementsEmpty={requirementsEmpty}
                  onRunStage={handleRunStage}
                  onVisualize={handleVisualize}
                />
              </Panel>

              <PanelResizeHandle className="w-px" />

              <Panel defaultSize={42} minSize={20}>
                <ConsolePane lines={consoleLines} onClear={clearConsole} />
              </Panel>

            </PanelGroup>
          </Panel>

          <PanelResizeHandle className="h-px" />

          <Panel defaultSize={38} minSize={15}>
            <VisualizerPane result={vizResult} isLoading={isVisualizing} />
          </Panel>

        </PanelGroup>
      ) : (
        /* ── Welcome screen ───────────────────────────────── */
        <div className="flex-1 flex flex-col items-center justify-center gap-8 px-4">

          {/* Logo block */}
          <div className="text-center">
            <h1 className="text-ide-text font-black text-5xl tracking-tight mb-3">LIPS IDE</h1>
            <p className="text-ide-muted text-sm max-w-sm leading-relaxed">
              LLM-driven Iterative Physics Simulation - generate, refine and visualise simulations with AI.
            </p>
          </div>

          {/* Feature badges */}
          <div className="flex gap-3 flex-wrap justify-center">
            {[
              { label: 'Write', color: '#a855f7', desc: 'Describe in English' },
              { label: 'Generate', color: '#3b82f6', desc: 'AI writes the code' },
              { label: 'Visualize', color: '#22c55e', desc: 'Interactive 3D output' },
            ].map(({ label, color, desc }) => (
              <div
                key={label}
                className="flex flex-col items-center gap-1.5 px-5 py-4 rounded-2xl"
                style={{ background: '#161616', border: '1px solid #2a2a2a', minWidth: '120px' }}
              >
                <span className="text-xs font-bold" style={{ color }}>{label}</span>
                <span className="text-ide-faint text-[11px] text-center">{desc}</span>
              </div>
            ))}
          </div>

          <button
            onClick={() => setShowNewProject(true)}
            className="btn-accent px-8 py-3 text-sm rounded-2xl font-bold"
          >
            + New Project
          </button>

          {workspaces.length > 0 && (
            <div className="flex flex-col items-center gap-2">
              <p className="text-ide-faint text-xs">or open an existing project</p>
              <select
                className="bg-ide-surface border border-ide-border text-ide-text text-xs rounded-xl px-3 py-2 focus:outline-none focus:border-ide-accent transition-colors font-sans"
                value=""
                onChange={e => e.target.value && handleSelectWorkspace(e.target.value)}
              >
                <option value="">— select project —</option>
                {workspaces.map(w => (
                  <option key={w} value={w}>{w}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      {showNewProject && (
        <NewProjectModal
          templates={templates}
          onClose={() => setShowNewProject(false)}
          onCreate={handleCreateWorkspace}
        />
      )}

      {showApiKey && (
        <ApiKeyModal
          currentMasked={apiKeyMasked}
          onClose={() => setShowApiKey(false)}
          onSaved={() => { loadApiKeyStatus(); setShowApiKey(false) }}
        />
      )}
    </div>
  )
}
