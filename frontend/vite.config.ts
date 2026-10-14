import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The board runs on 5173, which is the origin the FastAPI backend allows.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
})
