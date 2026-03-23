/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        dawn: '#FF6B4A',
        dusk: '#FFD4C8',
        rise: '#FFD966',
        moss: '#87A878',
        night: '#7A8FA8',
        sky: '#A8D8E8',
      },
      fontFamily: {
        sans: ['"DM Sans"', 'system-ui', '-apple-system', 'sans-serif'],
        serif: ['"DM Serif Display"', 'Georgia', 'serif'],
      },
    },
  },
  plugins: [],
}
