/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        phthalo: {
          DEFAULT: '#0B3D2E',
          deep: '#072A1F',
          mid: '#14705C',
          light: '#1A8F74',
          wash: '#E6F5F0',
          ghost: '#F3FAF7',
        },
        cream: '#FAFBF9',
        'ui-border': '#E2E5E0',
        'ui-text': '#1A1A1A',
        'ui-text-secondary': '#5A5A5A',
        'ui-text-tertiary': '#8A8A8A',
      },
      fontFamily: {
        display: ['Chakra Petch', 'sans-serif'],
        body: ['DM Sans', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
