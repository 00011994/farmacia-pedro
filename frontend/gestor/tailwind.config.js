/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50:  '#E6ECF7',
          100: '#C5D3EF',
          200: '#9CB2E2',
          300: '#7392D6',
          400: '#4A71CA',
          500: '#2151BE',
          600: '#0033A0',
          700: '#002D8C',
          800: '#002578',
          900: '#001D5C',
        },
        'max-red': {
          DEFAULT: '#E30613',
          dark:    '#B30410',
        },
        'max-yellow': '#FFD200',
        'whatsapp':   '#25D366',
        'success':    '#16A34A',
      },
      fontFamily: {
        sans: ['Poppins', 'Montserrat', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        pill: '999px',
      },
      boxShadow: {
        card:         '0 2px 8px rgba(0,0,0,0.08)',
        'card-hover': '0 6px 20px rgba(0,0,0,0.12)',
      },
    },
  },
  plugins: [],
}
