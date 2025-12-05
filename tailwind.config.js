/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './ui/templates/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        // StudyBuddyAI Cozy Yellow + Brown Palette - Enhanced
        // Warm yellows
        'warm-yellow': '#F7D774',
        'golden-yellow': '#F2C94C',
        'butter-yellow': '#FFEAA7',
        // Cream / beige backgrounds
        'warm-beige': '#FFF8E6',
        'cream': '#FAF3D7',
        'soft-cream': '#FFFAF0',
        // Cozy browns
        'cozy-brown': '#8B5E34',
        'caramel': '#A47148',
        'coffee': '#6F4E37',
        'soft-brown': '#9B7653',
        // Dark accents
        'dark-brown': '#4B2E16',
        'warm-gray': '#BFA585',
        'light-brown': '#D4A574',
        // Legacy mappings for compatibility
        'hoodie-orange': '#F2C94C',
        'navbar-dark': '#4B2E16',
        'teal': '#A47148',
        // Status colors (warm versions)
        'success': '#7CB342',
        'success-light': '#AED581',
        'warning': '#F2C94C',
        'error': '#D97706',
        'info': '#8B5E34',
      },
      fontFamily: {
        sans: ['Inter', 'Assistant', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
      },
      boxShadow: {
        'soft': '0 2px 8px rgba(0, 0, 0, 0.06)',
        'soft-lg': '0 4px 16px rgba(0, 0, 0, 0.08)',
        'warm': '0 4px 12px rgba(139, 94, 52, 0.15)',
        'warm-lg': '0 8px 24px rgba(139, 94, 52, 0.2)',
      },
    },
  },
  plugins: [],
}
