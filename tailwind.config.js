/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './ui/templates/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        // StudyBuddyAI warm palette
        'warm-beige': '#FFF4E5',
        'hoodie-orange': '#F6A623',
        'dark-brown': '#2B1B12',
        'teal': '#32B5A4',
        'navbar-dark': '#1C130E',
        'success': '#3BA55C',
        'warning': '#F9C74F',
        'error': '#F96A6A',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
