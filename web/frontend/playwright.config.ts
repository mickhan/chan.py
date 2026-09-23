import { defineConfig } from '@playwright/test'
export default defineConfig({ testDir: './e2e', use: { baseURL: 'http://127.0.0.1:8765', browserName: 'chromium', headless: true }, webServer: { command: '.venv/bin/python -m web', cwd: '../..', url: 'http://127.0.0.1:8765', reuseExistingServer: !process.env.CI, timeout: 30000 } })
