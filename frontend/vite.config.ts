import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({  }) => {
  let ret = {
    plugins: [react()],
    server: {
      port: 3000,
      historyApiFallback: true,
    },
  }
  return ret;
});

