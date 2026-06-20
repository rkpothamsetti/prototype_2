/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
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
          900: '#14532d',
        },
        accent: {
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
        },
        surface: {
          DEFAULT: '#f0fdf4',
          raised: '#ffffff',
          overlay: '#ecfdf5',
          border: '#bbf7d0',
        },
        violation: {
          critical: '#dc2626',
          high: '#d97706',
          low: '#16a34a',
        },
        status: {
          pending: '#d97706',
          confirmed: '#16a34a',
          rejected: '#6b7280',
          cleared: '#9ca3af',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.35s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      boxShadow: {
        glow: '0 4px 24px rgba(22, 163, 74, 0.12)',
        card: '0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(22, 163, 74, 0.08)',
      },
    },
  },
  plugins: [],
}
