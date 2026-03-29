import { Stage } from '../App'

interface Props {
  stages: Stage[]
  runningStage: string | null
  isVisualizing: boolean
  requirementsEmpty: boolean
  onRunStage: (stage: string) => void
  onVisualize: () => void
}

function Spinner() {
  return (
    <span
      className="inline-block w-3 h-3 rounded-full border-2 shrink-0"
      style={{
        borderColor: 'rgba(168,85,247,0.25)',
        borderTopColor: '#a855f7',
        animation: 'spin 0.7s linear infinite',
      }}
    />
  )
}

export default function ControlPanel({
  stages,
  runningStage,
  isVisualizing,
  requirementsEmpty,
  onRunStage,
  onVisualize,
}: Props) {
  const busy = runningStage !== null || isVisualizing
  const allStagesDone = stages.length > 0 && stages.every(s => s.has_output)
  const blocked = requirementsEmpty || busy || !allStagesDone

  return (
    <div className="flex flex-col h-full" style={{ background: '#111111', borderRight: '1px solid #222222' }}>

      {/* Header */}
      <div className="px-4 py-3 shrink-0" style={{ borderBottom: '1px solid #222222' }}>
        <span className="text-ide-muted text-[11px] font-semibold uppercase tracking-widest">Pipeline</span>
      </div>

      {/* Warning banner */}
      {requirementsEmpty && (
        <div className="mx-3 mt-3 p-3 rounded-xl shrink-0"
             style={{ background: 'rgba(234,179,8,0.06)', border: '1px solid rgba(234,179,8,0.2)' }}>
          <p className="text-ide-warning text-[11px] font-semibold mb-0.5">① Write your prompt first</p>
          <p className="text-[10px]" style={{ color: 'rgba(234,179,8,0.6)' }}>
            Edit <span className="font-mono">product-requirements.md</span>, save with Ctrl+S.
          </p>
        </div>
      )}

      {/* Stage list */}
      <div className="flex-1 overflow-y-auto px-3 py-3 flex flex-col">
        {stages.length === 0 && (
          <p className="text-ide-faint text-xs text-center mt-6">No stages found.</p>
        )}

        {stages.map((stage, idx) => {
          const isRunning = runningStage === stage.name
          const prevDone  = idx === 0 || stages[idx - 1].has_output
          const canRun    = !requirementsEmpty && !busy && prevDone

          let borderColor = '#2a2a2a'
          let bgColor     = 'transparent'
          let textColor   = '#666666'
          let dotColor    = '#444444'

          if (isRunning) {
            borderColor = 'rgba(168,85,247,0.5)'
            bgColor     = 'rgba(168,85,247,0.05)'
            textColor   = '#a855f7'
            dotColor    = '#a855f7'
          } else if (stage.has_output) {
            borderColor = 'rgba(34,197,94,0.3)'
            bgColor     = 'rgba(34,197,94,0.04)'
            textColor   = '#f0f0f0'
            dotColor    = '#22c55e'
          } else if (canRun) {
            textColor   = '#f0f0f0'
            dotColor    = '#555555'
          }

          return (
            <div key={stage.name}>
              <button
                disabled={!canRun}
                onClick={() => onRunStage(stage.name)}
                title={
                  requirementsEmpty
                    ? 'Write your prompt first'
                    : !prevDone
                    ? `Run '${stages[idx - 1].name}' first`
                    : `Run: python -m lips.compile ${stage.name}`
                }
                className="w-full rounded-xl px-3 py-2.5 text-left text-xs transition-all"
                style={{
                  border: `1px solid ${borderColor}`,
                  background: bgColor,
                  color: textColor,
                  cursor: canRun ? 'pointer' : 'not-allowed',
                  opacity: !canRun && !isRunning && !stage.has_output ? 0.4 : 1,
                }}
                onMouseEnter={e => {
                  if (canRun) {
                    (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(168,85,247,0.4)'
                    ;(e.currentTarget as HTMLButtonElement).style.background = 'rgba(168,85,247,0.04)'
                  }
                }}
                onMouseLeave={e => {
                  if (canRun && !isRunning) {
                    (e.currentTarget as HTMLButtonElement).style.borderColor = borderColor
                    ;(e.currentTarget as HTMLButtonElement).style.background = bgColor
                  }
                }}
              >
                <div className="flex items-center gap-2.5">
                  {/* Step number */}
                  <span className="text-[10px] font-mono shrink-0" style={{ color: '#444444' }}>
                    {String(idx + 1).padStart(2, '0')}
                  </span>

                  {/* Status indicator */}
                  <span className="shrink-0">
                    {isRunning ? (
                      <Spinner />
                    ) : stage.has_output ? (
                      <span className="text-xs font-bold" style={{ color: '#22c55e' }}>✓</span>
                    ) : (
                      <span className="w-2 h-2 rounded-full inline-block" style={{ background: dotColor }} />
                    )}
                  </span>

                  {/* Stage name */}
                  <span className="font-mono flex-1 truncate text-[11px]">{stage.name}</span>

                  {/* Run arrow */}
                  {canRun && !isRunning && (
                    <span className="shrink-0 text-xs" style={{ color: '#555555' }}>▶</span>
                  )}
                </div>
              </button>

              {/* Connector between stages */}
              {idx < stages.length - 1 && (
                <div className="stage-connector mx-auto w-fit">
                  <span /><span /><span />
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Divider */}
      <div className="mx-3" style={{ borderTop: '1px solid #222222' }} />

      {/* Visualize button */}
      <div className="px-3 py-3 shrink-0">
        <button
          disabled={blocked}
          onClick={onVisualize}
          title={
            requirementsEmpty
              ? 'Write your prompt first'
              : !allStagesDone
              ? 'Run all pipeline stages first'
              : 'Generate interactive visualization'
          }
          className="btn-accent w-full px-3 py-2.5 rounded-xl text-sm font-bold flex items-center justify-center gap-2"
        >
          {isVisualizing ? (
            <>
              <Spinner />
              <span>Visualizing…</span>
            </>
          ) : (
            <span>Visualize</span>
          )}
        </button>

        <p className="text-[10px] mt-2 text-center leading-relaxed" style={{ color: '#444444' }}>
          LLM generates an interactive HTML visualization
        </p>
      </div>

      {/* Legend */}
      <div className="px-3 py-2.5 shrink-0 space-y-1" style={{ borderTop: '1px solid #222222' }}>
        <div className="flex gap-2 items-center text-[10px]" style={{ color: 'rgba(34,197,94,0.7)' }}>
          <span>✓</span><span>Stage complete</span>
        </div>
        <div className="flex gap-2 items-center text-[10px]" style={{ color: '#444444' }}>
          <span className="w-2 h-2 rounded-full inline-block" style={{ background: '#444444' }} />
          <span>Not yet run</span>
        </div>
      </div>
    </div>
  )
}
