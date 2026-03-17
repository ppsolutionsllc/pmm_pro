/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      boxShadow: {
        soft: '0 10px 30px rgba(0,0,0,0.25)',
        glow: '0 0 0 1px rgba(74,222,128,0.15), 0 10px 30px rgba(0,0,0,0.35)',
        glowStrong: '0 0 0 1px rgba(74,222,128,0.25), 0 0 22px rgba(74,222,128,0.25), 0 16px 40px rgba(0,0,0,0.45)',
      },
      backgroundImage: {
        'radial-glow': 'radial-gradient(800px circle at var(--x, 50%) var(--y, 0%), rgba(74,222,128,0.12), transparent 60%)',
        'glass': 'linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02))',
        'accent-sheen': 'linear-gradient(120deg, transparent 0%, rgba(74,222,128,0.22) 15%, transparent 30%)',
      },
      keyframes: {
        floaty: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-6px)' },
        },
        modalIn: {
          '0%': { opacity: '0', transform: 'translateY(10px) scale(0.98)' },
          '100%': { opacity: '1', transform: 'translateY(0px) scale(1)' },
        },
        shimmer: {
          '0%': { transform: 'translateX(-120%)' },
          '100%': { transform: 'translateX(220%)' },
        },
        toastIn: {
          '0%': { opacity: '0', transform: 'translateX(18px) scale(0.98)' },
          '100%': { opacity: '1', transform: 'translateX(0px) scale(1)' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 0 1px rgba(74,222,128,0.12), 0 10px 30px rgba(0,0,0,0.35)' },
          '50%': { boxShadow: '0 0 0 1px rgba(74,222,128,0.25), 0 0 22px rgba(74,222,128,0.20), 0 16px 40px rgba(0,0,0,0.45)' },
        },
      },
      animation: {
        floaty: 'floaty 6s ease-in-out infinite',
        modalIn: 'modalIn 160ms ease-out both',
        shimmer: 'shimmer 1.4s ease-in-out infinite',
        toastIn: 'toastIn 220ms ease-out both',
        pulseGlow: 'pulseGlow 3.2s ease-in-out infinite',
      },
      colors: {
        mil: {
          50: '#e8eaed',
          100: '#c5c9d0',
          200: '#9fa6b0',
          300: '#798390',
          400: '#5c6979',
          500: '#3f4f61',
          600: '#374759',
          700: '#2d3c4e',
          800: '#243143',
          900: '#1a2332',
          950: '#0f1520',
        },
        accent: {
          DEFAULT: '#4ade80',
          dark: '#22c55e',
          light: '#86efac',
        },
        warn: '#f59e0b',
        danger: '#ef4444',
        surface: {
          DEFAULT: '#1e293b',
          light: '#273548',
          dark: '#0f172a',
          card: '#1a2535',
        }
      },
    },
  },
  plugins: [],
}
