import { useState } from 'react'
import axios from 'axios'

interface Props {
  currentMasked: string
  onClose: () => void
  onSaved: () => void
}

export default function ApiKeyModal({ currentMasked, onClose, onSaved }: Props) {
  const [value, setValue] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!value.trim()) { setErr('Please enter an API key.'); return }
    setBusy(true)
    setErr('')
    try {
      await axios.post('/api/config/apikey', { api_key: value.trim() })
      onSaved()
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
          <h2 className="text-ide-text font-bold text-lg tracking-tight">API Key</h2>
          <p className="text-xs mt-1.5" style={{ color: '#666666' }}>
            Mistral API key — saved to{' '}
            <code className="font-mono" style={{ color: '#888888' }}>lips-ide/.env</code>
          </p>
        </div>

        {currentMasked && (
          <div className="mb-5 px-3 py-2.5 rounded-xl flex items-center gap-2"
               style={{ background: 'rgba(34,197,94,0.05)', border: '1px solid rgba(34,197,94,0.2)' }}>
            <span className="text-xs" style={{ color: '#22c55e' }}>●</span>
            <span className="text-xs font-mono" style={{ color: '#22c55e' }}>{currentMasked}</span>
          </div>
        )}

        <label className="block text-[11px] font-semibold uppercase tracking-widest mb-2"
               style={{ color: '#666666' }}>
          {currentMasked ? 'Replace key' : 'Enter key'}
        </label>
        <input
          type="password"
          placeholder="sk-…"
          autoFocus
          className="w-full text-ide-text rounded-xl px-3 py-2.5 mb-5 text-xs font-mono focus:outline-none transition-colors"
          style={{ background: '#0f0f0f', border: '1px solid #2a2a2a' }}
          onFocus={e => (e.currentTarget.style.borderColor = '#a855f7')}
          onBlur={e => (e.currentTarget.style.borderColor = '#2a2a2a')}
          value={value}
          onChange={e => setValue(e.target.value)}
        />

        {err && (
          <div className="mb-5 px-3 py-2.5 rounded-xl text-xs"
               style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.25)', color: '#f87171' }}>
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
            {busy ? 'Saving…' : 'Save Key'}
          </button>
        </div>
      </form>
    </div>
  )
}
