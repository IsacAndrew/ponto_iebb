import { defineConfig } from "@playwright/test";
import { resolve } from "node:path";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  use: { baseURL: "http://127.0.0.1:5051", trace: "retain-on-failure" },
  webServer: {
    command: `${process.env.PONTO_TEST_PYTHON || resolve("../.venv/bin/python")} ../tests/serve_e2e.py`,
    url: "http://127.0.0.1:5051/health",
    reuseExistingServer: false,
  },
});
