import { useEffect, useRef } from 'react'
import { ConsoleLine } from '../App'

interface Props {
  lines: ConsoleLine[]
  onClear: () => void
}

const colorMap: Record<ConsoleLine['type'], string> = {
  info:    '#a855f7',
  stdout:  'rgba(240,240,240,0.75)',
  success: '#22c55e',
  error:   '#f87171',
  system:  '#555555',
}

export default function ConsolePane({ lines, onClear }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines])

  return (
    <div className="flex flex-col h-full" style={{ background: '#0f0f0f', borderLeft: '1px solid #222222' }}>

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 shrink-0"
           style={{ background: '#111111', borderBottom: '1px solid #222222' }}>
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: '#666666' }}>
            Console
          </span>
          {lines.length > 0 && (
            <span className="text-[10px] font-mono" style={{ color: '#444444' }}>{lines.length}</span>
          )}
        </div>
        <button
          onClick={onClear}
          className="text-[10px] px-2 py-0.5 rounded-lg transition-colors"
          style={{ color: '#555555' }}
          onMouseEnter={e => (e.currentTarget.style.color = '#888888')}
          onMouseLeave={e => (e.currentTarget.style.color = '#555555')}
          title="Clear console"
        >
          Clear
        </button>
      </div>

      {/* Terminal output */}
      <div
        className="flex-1 overflow-y-auto px-4 py-3 font-mono text-xs leading-relaxed"
        style={{ background: '#0a0a0a' }}
      >
        {lines.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2" style={{ color: '#333333' }}>
            <span className="text-2xl">▸</span>
            <p className="text-[11px]">Run a pipeline stage to see output.</p>
          </div>
        ) : (
          <>
            {lines.map((line, i) => (
              <span
                key={i}
                className="whitespace-pre-wrap break-all"
                style={{ color: colorMap[line.type] }}
              >
                {line.text}
              </span>
            ))}
            {/* Blinking cursor */}
            <span
              className="inline-block w-2 h-3.5 align-text-bottom ml-0.5 animate-pulse-dot"
              style={{ background: 'rgba(168,85,247,0.6)' }}
            />
          </>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
