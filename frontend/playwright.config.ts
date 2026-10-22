import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './e2e', fullyParallel: false, workers: 1, timeout: 30000,
  use: { baseURL: process.env.APP_URL || 'http://127.0.0.1:8651', channel: 'chrome', headless: true, screenshot: 'only-on-failure', trace: 'retain-on-failure' },
  reporter: [['list'], ['json', {outputFile:'test-results/results.json'}]],
})
