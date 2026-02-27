/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Minimal dark theme – same vibe as Tkinter, cleaner
        surface: '#0a0a0a',
        card: '#141414',
        sidebar: '#0f0f0f',
        header: '#111111',
        accent: '#e5a00d',
        'accent-soft': '#f5d078',
        success: '#22c55e',
        danger: '#ef4444',
        'text-muted': '#a1a1aa',
        'text-dim': '#71717a',
        border: '#27272a',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
