// Desktop browser smoke check using the same manifest/path rules as Android.
// Uses the installed browser and Playwright; no captured source is modified.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require('playwright');

(async () => {
  const root = path.resolve(__dirname, '..');
  const dir = path.join(root, 'sites', 'modeldial');
  const m = JSON.parse(fs.readFileSync(path.join(dir, 'manifest.json'), 'utf8'));
  const exact = new Map(m.entries.map(e => [e.url, e]));
  const paths = new Map();
  const missing = [], errors = [], pageErrors = [], requests = [];
  for (const e of m.entries) {
    const u = new URL(e.url); u.search = ''; paths.set(u.href, e);
  }
  const port = Number(process.env.OFFLINE_QA_PORT || 18092);
  const server = http.createServer((req, res) => {
    const u = new URL(req.url, `http://127.0.0.1:${port}`);
    const remote = u.pathname.startsWith('/_remote/')
      ? u.pathname.slice(9).replace('/', '://') + u.search
      : `https://modeldial.com${u.pathname}${u.search}`;
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', '*');
    res.setHeader('Cache-Control', 'no-store');
    if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }
    if (remote.includes('/api/metrics/page-view')) {
      res.setHeader('Content-Type', 'application/json'); res.end('{}'); return;
    }
    const clean = new URL(remote); clean.search = '';
    const e = exact.get(remote) || paths.get(clean.href);
    if (!e) { missing.push(remote); res.writeHead(404); res.end('not mirrored'); return; }
    res.setHeader('Content-Type', e.contentType);
    res.end(fs.readFileSync(path.join(dir, e.path)));
  });
  await new Promise(resolve => server.listen(port, '127.0.0.1', resolve));
  const browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true,
  });
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    requests.push(url.href);
    if (url.hostname === '127.0.0.1') return route.continue();
    const remote = `http://127.0.0.1:${port}/_remote/${url.protocol.slice(0,-1)}/${url.host}${url.pathname}${url.search}`;
    const response = await route.fetch({ url: remote });
    await route.fulfill({ response });
  });
  const page = await context.newPage();
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', e => pageErrors.push(e.message));
  await page.goto(`http://127.0.0.1:${port}/radar`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  const before = await page.locator('body').innerText();
  const buttons = await page.locator('button').evaluateAll(xs => xs.map(x => ({
    text: x.textContent.trim(), action: x.getAttribute('data-action'),
    axis: x.getAttribute('data-axis'), title: x.title, aria: x.getAttribute('aria-label'),
  })));
  fs.mkdirSync(path.join(root, 'qa'), { recursive: true });
  await page.screenshot({ path: path.join(root, 'qa', 'modeldial-radar-desktop.png'), fullPage: false });
  const interactions = [];
  const axisButtons = await page.locator('[data-action="axis"]').evaluateAll(xs => xs.map(x => ({
    text: x.textContent.trim(), axis: x.getAttribute('data-score-axis'),
  })));
  for (let i = 0; i < axisButtons.length; i++) {
    const button = axisButtons[i];
    await page.locator('[data-action="axis"]').nth(i).click();
    await page.waitForTimeout(450);
    interactions.push({ type: 'axis', ...button, url: page.url(),
      bodyLength: (await page.locator('body').innerText()).length });
  }
  await page.locator('[data-action="axis"]').first().click();
  await page.waitForTimeout(500);
  await page.locator('[data-action="view"]').nth(1).click();
  await page.waitForTimeout(500);
  interactions.push({ type: 'chart', url: page.url(), canvas: await page.locator('canvas').count(),
    svg: await page.locator('svg').count() });
  await page.screenshot({ path: path.join(root, 'qa', 'modeldial-chart-desktop.png'), fullPage: false });
  const inputs = await page.locator('input').evaluateAll(xs => xs.map(x => ({ placeholder: x.placeholder, type: x.type })));
  const search = page.locator('input[placeholder*="搜索模型"]').first();
  if (await search.count()) {
    await search.fill('claude'); await page.waitForTimeout(500);
    interactions.push({ type: 'search', value: 'claude', bodyLength: (await page.locator('body').innerText()).length });
    await search.fill('');
  }
  await page.locator('a.locale-link').first().click();
  await page.waitForTimeout(1500);
  interactions.push({ type: 'language', url: page.url(), lang: await page.locator('html').getAttribute('lang') });
  const result = { engine: await browser.version(), title: await page.title(),
    bodyLength: before.length, buttons, inputs, interactions,
    missing: [...new Set(missing)], errors, pageErrors, requests: [...new Set(requests)] };
  const visitedAxes = new Set(interactions.filter(x => x.type === 'axis').map(x => new URL(x.url).searchParams.get('axis')));
  const expectedAxes = ['overall', 'backend', 'frontend', 'knowledge', 'aesthetic', 'maintainability'];
  result.passed = result.missing.length === 0 && errors.length === 0 && pageErrors.length === 0 &&
    expectedAxes.every(axis => visitedAxes.has(axis)) &&
    interactions.some(x => x.type === 'chart' && new URL(x.url).searchParams.get('view') === 'cost') &&
    interactions.some(x => x.type === 'search' && x.bodyLength < before.length) &&
    interactions.some(x => x.type === 'language' && x.lang === 'en');
  fs.writeFileSync(path.join(root, 'qa', 'modeldial-desktop.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify({ title: result.title, bodyLength: before.length,
    passed: result.passed, buttonCount: buttons.length, interactions, missing: result.missing, errors, pageErrors }, null, 2));
  await browser.close();
  await new Promise(resolve => server.close(resolve));
  if (!result.passed) process.exitCode = 1;
})().catch(e => { console.error(e); process.exit(1); });
