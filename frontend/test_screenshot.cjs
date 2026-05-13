const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: "new" });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  console.log('Navigating...');
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' });
  await page.screenshot({ path: 'test_screenshot.png' });
  
  const html = await page.content();
  const fs = require('fs');
  fs.writeFileSync('test_html.html', html);
  
  console.log('Done.');
  await browser.close();
})();
