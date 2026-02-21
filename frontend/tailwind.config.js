/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Brand colors from FreeFood UCD logo
        brand: {
          cyan: '#03daff',
          red: '#fa3000',
          yellow: '#ffbc03',
          brown: '#d96504',
        },
        // Semantic colors
        primary: {
          DEFAULT: '#03daff',
          light: '#5ee4ff',
          dark: '#02b8d9',
        },
        danger: {
          DEFAULT: '#fa3000',
          light: '#ff6b47',
          dark: '#d12800',
        },
        warning: {
          DEFAULT: '#ffbc03',
          light: '#ffd24d',
          dark: '#d99d02',
        },
        accent: {
          DEFAULT: '#d96504',
          light: '#ff8833',
          dark: '#b35403',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
      },
      boxShadow: {
        'card': '0 2px 8px rgba(0, 0, 0, 0.08)',
        'card-hover': '0 4px 16px rgba(0, 0, 0, 0.12)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-slow': 'bounce 2s infinite',
      },
    },
  },
  plugins: [],
};

// Made with Bob
