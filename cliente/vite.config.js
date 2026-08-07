import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
    plugins: [react()],
    build: {
        // El build queda donde Django lo recoge para servirlo. Así en
        // producción todo sale de un solo origen y la cookie de sesión no
        // necesita SameSite=None ni protección CSRF aparte.
        outDir: '../static_build',
        emptyOutDir: true,
    },
    server: {
        port: 5173,
        // Las peticiones a la API se reenvían al backend de Django. Así el
        // navegador las ve como del mismo origen y la cookie de sesión viaja
        // sin necesidad de SameSite=None, que obligaría a proteger contra
        // CSRF por separado.
        proxy: {
            '/auth': 'http://127.0.0.1:8000',
            '/citas': 'http://127.0.0.1:8000',
            '/servicios': 'http://127.0.0.1:8000',
            '/barberos': 'http://127.0.0.1:8000',
            '/clientes': 'http://127.0.0.1:8000',
        },
    },
});
