/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Cascadia Code', 'monospace'],
      },
      colors: {
        ide: {
          bg:           '#0f0f0f',
          surface:      '#161616',
          panel:        '#1c1c1c',
          border:       '#2a2a2a',
          'border-soft':'#222222',
          text:         '#f0f0f0',
          muted:        '#888888',
          faint:        '#444444',
          accent:       '#a855f7',
          'accent-dim': '#7c3aed',
          green:        '#22c55e',
          pink:         '#ec4899',
          blue:         '#3b82f6',
          yellow:       '#eab308',
          success:      '#22c55e',
          warning:      '#eab308',
          error:        '#f87171',
        },
      },
      boxShadow: {
        'card':   '0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.6)',
        'lift':   '0 4px 12px rgba(0,0,0,0.5), 0 2px 4px rgba(0,0,0,0.4)',
        'modal':  '0 20px 60px rgba(0,0,0,0.7), 0 8px 24px rgba(0,0,0,0.5)',
        'accent': '0 0 0 1px rgba(168,85,247,0.4)',
      },
    },
  },
  plugins: [],
}
