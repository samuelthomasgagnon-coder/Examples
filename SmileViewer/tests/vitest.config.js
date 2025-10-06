import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    react({
      // Transform JSX in .js, .jsx, .ts, .tsx (both app and tests)
      include: [
        /\.[jt]sx?$/,
      ],
    }),
  ],
  test: {
    environment: 'jsdom',
    setupFiles: ['tests/vitest.setup.js'],
    globals: true,
    coverage: {
      reporter: ['text', 'html'],
    },
  },
})
