const { test, expect } = require('@playwright/test');

test.use({
  launchOptions: {
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  },
  viewport: { width: 1440, height: 2200 },
});

test('legacy shell renders unopened rows without draw result leakage', async ({ page }) => {
  await page.goto('http://127.0.0.1:3000/legacy-shell', { waitUntil: 'domcontentloaded', timeout: 120000 });
  const iframe = page.frameLocator('iframe.legacy-shell-frame');
  await expect(iframe.locator('body')).toContainText('127期', { timeout: 120000 });
  await page.waitForTimeout(8000);
  const bodyText = await iframe.locator('body').innerText();
  const lines = bodyText.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  const focus = lines.filter(line => /127期|126期|125期|一句真言|欲钱买特码|欲钱解特|单双四肖/.test(line));
  console.log('FOCUS_LINES_START');
  for (const line of focus.slice(0, 120)) console.log(line);
  console.log('FOCUS_LINES_END');
  await page.screenshot({ path: 'd:/pythonProject/outsource/Liuhecai/tmp_legacy_shell.png', fullPage: true });
});
