import react from '@vitejs/plugin-react'
export default { plugins: [react()], build: { target: 'es2022' }, server: { host: '127.0.0.1', fs: { allow: ['..'] } }, resolve: { dedupe: ['react', 'react-dom'] } }
