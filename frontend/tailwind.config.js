/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#0f4c3a', // Primary deep green
          950: '#062d22',
        },
        mint: {
          50: '#f4fbf7',
          100: '#e6f4ea', // Muted mint highlight
          200: '#c7ebd1',
          300: '#9ddcb0',
          500: '#34a853',
          700: '#0d6849',
        },
        surface: {
          DEFAULT: '#ffffff',
          muted: '#f8fafc',
          subtle: '#f1f5f9',
          border: '#e2e8f0',
        },
        severity: {
          low: {
            bg: '#f1f5f9',
            text: '#334155',
            border: '#cbd5e1',
          },
          medium: {
            bg: '#fef3c7',
            text: '#92400e',
            border: '#fde68a',
          },
          high: {
            bg: '#fee2e2',
            text: '#991b1b',
            border: '#fecaca',
          },
          critical: {
            bg: '#ffe4e6',
            text: '#881337',
            border: '#fecdd3',
          },
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'sans-serif',
        ],
        mono: [
          'JetBrains Mono',
          'SFMono-Regular',
          'Menlo',
          'Monaco',
          'Consolas',
          'monospace',
        ],
      },
    },
  },
  plugins: [],
}
