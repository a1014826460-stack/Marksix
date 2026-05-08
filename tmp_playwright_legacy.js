const { chromium } = require('playwright');
(async() => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe'
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 2200 } });
  await page.goto('http://127.0.0.1:3000/legacy-shell', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('iframe.legacy-shell-frame', { timeout: 120000 });
  const iframeHandle = await page.locator('iframe.legacy-shell-frame').elementHandle();
  const frame = await iframeHandle.contentFrame();
  if (!frame) throw new Error('iframe not ready');
  await frame.waitForLoadState('domcontentloaded', { timeout: 120000 });
  await page.waitForTimeout(8000);
  const bodyText = await frame.locator('body').innerText();
  const lines = bodyText.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  const focus = lines.filter(line => /127期|126期|125期|一句真言|欲钱买特码|欲钱解特|单双四肖/.test(line));
  console.log('FOCUS_LINES_START');
  for (const line of focus.slice(0, 80)) console.log(line);
  console.log('FOCUS_LINES_END');
  await page.screenshot({ path: 'd:/pythonProject/outsource/Liuhecai/tmp_legacy_shell.png', fullPage: true });
  await browser.close();
})();
