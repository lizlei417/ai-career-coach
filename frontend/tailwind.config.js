/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: { 950: '#0B1320', 900: '#111B2B', 800: '#1A2638', 700: '#26344A', 600: '#3A4A62', 500: '#56667E' },
        paper: { DEFAULT: '#F5F6F8', 50: '#FAFBFC', 100: '#F1F3F6', 200: '#E6E9EE', 300: '#D5DAE2' },
        accent: { 50: '#EEF3F9', 100: '#DCE6F2', 200: '#B9CCE3', 400: '#5F84AE', 500: '#3F6896', 600: '#2F5682', 700: '#24456B' },
        ok: { 50: '#EEF6F1', 500: '#3D7A5A', 600: '#2F6449' },
        warn: { 50: '#FBF5EA', 200: '#EED9B0', 500: '#A3742A', 600: '#86601F' },
        miss: { 50: '#F4F4F6', 500: '#6B7280' },
      },
      fontFamily: {
        serif: ['"Source Serif 4"', '"Noto Serif SC"', '"Noto Serif TC"', '"Songti SC"', 'serif'],
        sans: ['Inter', '"Noto Sans SC"', '"PingFang SC"', '"Microsoft YaHei"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        hair: '0 0 0 1px rgba(17,27,43,0.06)',
        soft: '0 1px 2px rgba(17,27,43,0.04), 0 4px 16px -6px rgba(17,27,43,0.08)',
        lift: '0 2px 4px rgba(17,27,43,0.05), 0 16px 40px -12px rgba(17,27,43,0.18)',
      },
      keyframes: {
        rise: { '0%': { opacity: 0, transform: 'translateY(6px)' }, '100%': { opacity: 1, transform: 'none' } },
        fade: { '0%': { opacity: 0 }, '100%': { opacity: 1 } },
        shimmer: { '0%': { backgroundPosition: '-400px 0' }, '100%': { backgroundPosition: '400px 0' } },
      },
      animation: {
        rise: 'rise .35s cubic-bezier(.2,.7,.2,1) both',
        fade: 'fade .3s ease both',
        shimmer: 'shimmer 1.4s linear infinite',
      },
    },
  },
  plugins: [],
}
