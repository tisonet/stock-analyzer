/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'strong-buy': '#22c55e',
        'buy': '#3b82f6',
        'hold': '#eab308',
        'avoid': '#ef4444',
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}
