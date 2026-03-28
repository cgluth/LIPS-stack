import { useState } from 'react'
import { VizResult } from '../App'

interface Props {
  result: VizResult | null
  isLoading: boolean
}

export default function VisualizerPane({ result, isLoading }: Props) {
  const [showScript, setShowScript] = useState(false)

  const script = result && 'script' in result ? result.script : null

  return (
    <div className="flex flex-col h-full" style={{ background: '#0f0f0f', borderTop: '1px solid #222222' }}>

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 shrink-0"
           style={{ background: '#111111', borderBottom: '1px solid #222222' }}>
        <div className="flex items-center gap-3">
          <span className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: '#666666' }}>
            Visualizer
          </span>
          {result && !('error' in result) && !isLoading && (
            <span className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                  style={{ border: '1px solid rgba(34,197,94,0.3)', color: '#22c55e', background: 'rgba(34,197,94,0.05)' }}>
              live
            </span>
          )}
        </div>
        {script && (
          <button
            onClick={() => setShowScript(s => !s)}
            className="text-[10px] px-2 py-0.5 rounded-lg transition-colors"
            style={{ color: '#555555' }}
            onMouseEnter={e => (e.currentTarget.style.color = '#888888')}
            onMouseLeave={e => (e.currentTarget.style.color = '#555555')}
          >
            {showScript ? 'Show Output' : 'Show Script'}
          </button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-auto flex items-center justify-center">

        {/* Loading */}
        {isLoading && (
          <div className="flex flex-col items-center gap-4" style={{ color: '#666666' }}>
            <div
              className="w-8 h-8 rounded-full border-2"
              style={{
                borderColor: 'rgba(168,85,247,0.2)',
                borderTopColor: '#a855f7',
                animation: 'spin 0.8s linear infinite',
              }}
            />
            <div className="text-center">
              <p className="text-xs" style={{ color: 'rgba(240,240,240,0.5)' }}>Generating visualization…</p>
              <p className="text-[10px] mt-1" style={{ color: '#444444' }}>The LLM is writing interactive HTML</p>
            </div>
          </div>
        )}

        {/* Script view */}
        {!isLoading && result && showScript && script && (
          <pre className="w-full h-full overflow-auto p-4 text-xs font-mono leading-relaxed whitespace-pre-wrap"
               style={{ color: 'rgba(240,240,240,0.7)', background: '#0a0a0a' }}>
            {script}
          </pre>
        )}

        {/* PNG image */}
        {!isLoading && !showScript && result && 'type' in result && result.type === 'image' && (
          <img
            src={`data:image/png;base64,${result.data}`}
            alt="Simulation visualization"
            className="max-w-full max-h-full object-contain p-2"
          />
        )}

        {/* Interactive HTML */}
        {!isLoading && !showScript && result && 'type' in result && result.type === 'html' && (
          <iframe
            srcDoc={result.data}
            className="w-full h-full border-none"
            sandbox="allow-scripts allow-same-origin"
            title="Simulation visualization"
          />
        )}

        {/* Error */}
        {!isLoading && !showScript && result && 'error' in result && (
          <div className="flex flex-col items-center gap-3 max-w-lg text-center p-8">
            <div className="w-11 h-11 rounded-full flex items-center justify-center"
                 style={{ border: '1px solid rgba(248,113,113,0.3)', background: 'rgba(248,113,113,0.05)' }}>
              <span className="text-lg" style={{ color: '#f87171' }}>✗</span>
            </div>
            <div>
              <p className="text-sm font-semibold mb-1" style={{ color: '#f87171' }}>Visualization failed</p>
              <p className="text-[11px]" style={{ color: '#555555' }}>The LLM could not generate a valid output</p>
            </div>
            <pre className="text-xs whitespace-pre-wrap text-left rounded-xl p-4 w-full max-h-40 overflow-auto font-mono"
                 style={{ color: '#888888', background: '#161616', border: '1px solid #2a2a2a' }}>
              {result.error}
            </pre>
            {script && (
              <button
                onClick={() => setShowScript(true)}
                className="text-xs transition-colors"
                style={{ color: '#a855f7' }}
                onMouseEnter={e => (e.currentTarget.style.color = '#c084fc')}
                onMouseLeave={e => (e.currentTarget.style.color = '#a855f7')}
              >
                View generated script →
              </button>
            )}
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !result && (
          <div className="flex flex-col items-center gap-3 text-center" style={{ color: '#444444' }}>
            <div className="w-14 h-14 rounded-full flex items-center justify-center"
                 style={{ border: '1px solid #2a2a2a' }}>
              <span className="text-3xl" style={{ color: '#333333' }}>◎</span>
            </div>
            <div>
              <p className="text-sm font-medium" style={{ color: '#555555' }}>No visualization yet</p>
              <p className="text-[11px] mt-1">
                Run all pipeline stages, then click{' '}
                <strong style={{ color: '#888888' }}>Visualize</strong>.
              </p>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
