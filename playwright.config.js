import config from './frontend/playwright.config.js';
export default {
  ...config,
  testDir: './frontend/e2e',
};

