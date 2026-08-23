/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#070914',
        surface: '#0d1117',
        border: '#1e2433',
        accent: {
          DEFAULT: '#a78bfa',
          hover: '#c084fc',
        },
      },
    },
  },
  plugins: [],
}
