/** @type {import('tailwindcss').Config} */
export default {
    darkMode: 'class',
    content: [
        './index.html',
        './**/*.{ts,tsx}',
        './pages/**/*.{ts,tsx}',
        './src/**/*.{ts,tsx}',
        './components/**/*.{ts,tsx}',
    ],
    theme: {
        extend: {
            colors: {
                primary: '#13b6ec',
                'background-light': '#f6f8f8',
                'background-dark': '#101d22',
                'surface-dark': '#1a2c33',
                'surface-light': '#ffffff',
            },
            fontFamily: {
                display: ['Inter', 'sans-serif'],
            },
        },
    },
    plugins: [
        require('@tailwindcss/forms'),
    ],
};
