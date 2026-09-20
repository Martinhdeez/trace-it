import { defineConfig, devices } from '@playwright/test'

const baseURL = process.env.TRACE_E2E_URL ?? 'http://127.0.0.1:18174/nexia/trace-it/'
const target = new URL(baseURL)
// These tests create data. Never point them at the public deployment.
if (!['127.0.0.1', 'localhost'].includes(target.hostname)) {
  throw new Error('Browser E2E requires an isolated local stack')
}

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 45_000,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
