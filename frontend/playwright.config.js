import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  use: { baseURL: 'http://127.0.0.1:5174', channel: 'chrome', headless: true, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  webServer: [
    { command: `"${path.join(root, '.venv/Scripts/python.exe')}" "${path.join(root, 'scripts/e2e_backend.py')}"`, url: 'http://127.0.0.1:8001/api/v1/posts/1', timeout: 60000, reuseExistingServer: false },
    { command: 'npm run dev -- --port 5174', url: 'http://127.0.0.1:5174', env: { API_PROXY_TARGET: 'http://127.0.0.1:8001' }, timeout: 30000, reuseExistingServer: false },
  ],
})
