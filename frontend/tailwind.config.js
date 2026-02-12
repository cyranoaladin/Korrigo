/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{vue,js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
            },
            colors: {
                primary: {
                    50: '#eef4ff',
                    100: '#dbe8ff',
                    200: '#b8d2ff',
                    300: '#8db4ff',
                    400: '#5e8cff',
                    500: '#3a63f3',
                    600: '#2748d8',
                    700: '#1f3aad',
                    800: '#1c318a',
                    900: '#192e6d',
                },
                neutralDark: '#1f2937',
                borderSoft: '#e5e7eb',
                success: '#15803d',
                warning: '#b45309',
                danger: '#b91c1c'
            }
        },
    },
    plugins: [],
}
