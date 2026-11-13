/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        mirai: {
          bg: '#0B0F19',
          card: '#111827',
          border: '#1F2937',
          accent: '#3B82F6',
          success: '#10B981',
          danger: '#EF4444',
          warning: '#F59E0B',
          muted: '#9CA3AF',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Courier New', 'monospace'],
      }
    },
  },
  plugins: [],
}
