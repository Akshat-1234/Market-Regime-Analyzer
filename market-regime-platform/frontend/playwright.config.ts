import { defineConfig, devices } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const here=path.dirname(fileURLToPath(import.meta.url));
export default defineConfig({
  testDir:'./e2e',timeout:30_000,expect:{timeout:10_000},fullyParallel:false,retries:0,
  reporter:'list',use:{baseURL:'http://127.0.0.1:5173',trace:'retain-on-failure',...devices['Desktop Chrome']},
  webServer:[
    {command:'python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000',cwd:path.resolve(here,'..'),url:'http://127.0.0.1:8000/api/health',reuseExistingServer:true,timeout:60_000},
    {command:'npm run dev -- --host 0.0.0.0 --port 5173',cwd:here,url:'http://127.0.0.1:5173',reuseExistingServer:true,timeout:60_000}
  ]
});
