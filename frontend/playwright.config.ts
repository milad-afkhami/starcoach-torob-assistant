import { defineConfig } from '@playwright/test'
import {fileURLToPath} from 'node:url'
export default defineConfig({
  globalSetup: './e2e/setup.ts',
  testDir: './e2e', fullyParallel: false, workers: 1, timeout: 30000,
  use: { storageState: fileURLToPath(new URL('../data/ui-test-session.json',import.meta.url)), baseURL: process.env.APP_URL || 'http://127.0.0.1:8651', channel: 'chrome', headless: true, screenshot: 'only-on-failure', trace: 'retain-on-failure' },
  reporter: [['list'], ['json', {outputFile:'test-results/results.json'}]],
})
