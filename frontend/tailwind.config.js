/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Lightspeed brand colors
        dawn: '#FF6B4A',
        dusk: '#FFD4C8',
        rise: '#FFD966',
        ray: '#FFF4B3',
        moss: '#87A878',
        glow: '#C8E6A0',
        night: '#7A8FA8',
        sky: '#A8D8E8',
        
        // Semantic aliases
        primary: '#FF6B4A',    // dawn
        secondary: '#7A8FA8',  // night
        success: '#87A878',    // moss
        warning: '#FFD966',    // rise
        info: '#A8D8E8',       // sky
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

