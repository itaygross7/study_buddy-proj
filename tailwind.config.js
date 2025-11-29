/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './ui/templates/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        // StudyBuddyAI Cozy Yellow + Brown Palette
        // Warm yellows
        'warm-yellow': '#F7D774',
        'golden-yellow': '#F2C94C',
        // Cream / beige backgrounds
        'warm-beige': '#FFF8E6',
        'cream': '#FAF3D7',
        // Cozy browns
        'cozy-brown': '#8B5E34',
        'caramel': '#A47148',
        'coffee': '#6F4E37',
        // Dark accents
        'dark-brown': '#4B2E16',
        'warm-gray': '#BFA585',
        // Legacy mappings for compatibility
        'hoodie-orange': '#F2C94C',
        'navbar-dark': '#4B2E16',
        'teal': '#A47148',
        // Status colors (warm versions)
        'success': '#7CB342',
        'warning': '#F2C94C',
        'error': '#D97706',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
