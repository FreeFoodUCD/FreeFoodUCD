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
        // Logo-inspired artistic minimal palette
        primary: {
          DEFAULT: '#F78620', // Warm orange/brown from logo - friendly, approachable
          light: '#FFA04D',
          dark: '#E06D0A',
        },
        secondary: {
          DEFAULT: '#FFC613', // Yellow from logo - energetic, optimistic
          light: '#FFD54D',
          dark: '#E6B000',
        },
        accent: {
          DEFAULT: '#6FC266', // Green from logo - fresh, positive
          light: '#8FD88A',
          dark: '#5AAA52',
        },
        text: {
          DEFAULT: '#1A1A1A', // Deep black
          light: '#4B5563',
          lighter: '#9CA3AF',
        },
        danger: {
          DEFAULT: '#DC2626',
          light: '#FCA5A5',
          dark: '#991B1B',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
        '4xl': '2.5rem',
      },
      boxShadow: {
        'soft': '0 2px 12px rgba(47, 128, 237, 0.08)',
        'soft-hover': '0 4px 20px rgba(47, 128, 237, 0.12)',
        'warm': '0 2px 12px rgba(255, 183, 3, 0.15)',
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
