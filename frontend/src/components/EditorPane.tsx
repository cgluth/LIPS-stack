import MonacoEditor from '@monaco-editor/react'

interface Props {
  workspace: string
  fileList: string[]
  activeFile: string
  content: string
  isDirty: boolean
  onChange: (value: string | undefined) => void
  onSave: () => void
  onSelectFile: (path: string) => void
}

function langFor(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase() ?? ''
  const map: Record<string, string> = {
    py: 'python', md: 'markdown', json: 'json',
    html: 'html', puml: 'plaintext', txt: 'plaintext',
    yaml: 'yaml', yml: 'yaml',
  }
  return map[ext] ?? 'plaintext'
}

function groupByStage(files: string[]): Record<string, string[]> {
  const groups: Record<string, string[]> = {}
  for (const f of files) {
    const stage = f.split('/')[0]
    if (!groups[stage]) groups[stage] = []
    groups[stage].push(f)
  }
  return groups
}

export default function EditorPane({
  fileList,
  activeFile,
  content,
  isDirty,
  onChange,
  onSave,
  onSelectFile,
}: Props) {
  const isRequirementsFile = activeFile.endsWith('product-requirements.md')
  const showStartBanner = isRequirementsFile && content.trim() === ''
  const groups = groupByStage(fileList)

  return (
    <div className="flex flex-col h-full" style={{ background: '#0f0f0f' }}>

      {/* File selector bar */}
      <div className="flex items-center gap-2 px-3 py-2 shrink-0"
           style={{ background: '#111111', borderBottom: '1px solid #222222' }}>
        <select
          className="flex-1 min-w-0 text-ide-text text-xs rounded-xl px-2.5 py-1.5 focus:outline-none transition-colors font-mono"
          style={{ background: '#1c1c1c', border: '1px solid #2a2a2a' }}
          value={activeFile}
          onChange={e => onSelectFile(e.target.value)}
        >
          {Object.entries(groups).map(([stage, files]) => (
            <optgroup key={stage} label={stage}>
              {files.map(f => (
                <option key={f} value={f}>
                  {f.replace(`${stage}/`, '')}
                </option>
              ))}
            </optgroup>
          ))}
        </select>

        <button
          onClick={onSave}
          title="Save (Ctrl+S)"
          className="shrink-0 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all"
          style={isDirty ? {
            border: '1px solid rgba(234,179,8,0.5)',
            color: '#eab308',
            background: 'rgba(234,179,8,0.05)',
          } : {
            border: '1px solid #2a2a2a',
            color: '#555555',
            background: 'transparent',
          }}
        >
          {isDirty ? '● Save' : '✓ Saved'}
        </button>
      </div>

      {/* Breadcrumb */}
      <div className="px-3 py-1 text-[11px] shrink-0 truncate font-mono"
           style={{ background: '#111111', borderBottom: '1px solid #1e1e1e', color: '#555555' }}>
        {activeFile}
      </div>

      {/* "Start here" banner */}
      {showStartBanner && (
        <div className="px-4 py-3 shrink-0 text-xs leading-relaxed"
             style={{
               borderBottom: '1px solid rgba(168,85,247,0.2)',
               background: 'rgba(168,85,247,0.04)',
               color: 'rgba(168,85,247,0.9)',
             }}>
          <span className="font-bold" style={{ color: '#a855f7' }}>① Start here.</span>{' '}
          Describe your physics simulation in this file, then press{' '}
          <kbd className="px-1.5 py-0.5 rounded-lg font-mono text-[10px]"
               style={{ background: '#1c1c1c', border: '1px solid #2a2a2a', color: '#f0f0f0' }}>
            Ctrl+S
          </kbd>{' '}
          to save, then run the pipeline stages in order.
        </div>
      )}

      {/* Monaco */}
      <div className="flex-1 min-h-0">
        <MonacoEditor
          height="100%"
          language={langFor(activeFile)}
          value={content}
          onChange={onChange}
          theme="vs-dark"
          options={{
            fontSize: 13,
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            minimap: { enabled: false },
            lineNumbers: 'on',
            wordWrap: 'on',
            scrollBeyondLastLine: false,
            renderWhitespace: 'none',
            padding: { top: 8, bottom: 8 },
            smoothScrolling: true,
          }}
          onMount={(editor, monaco) => {
            editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, onSave)
          }}
        />
      </div>
    </div>
  )
}
