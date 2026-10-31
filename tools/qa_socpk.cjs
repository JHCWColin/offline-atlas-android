// Exercise the unmodified SOCPK snapshot using a manifest-only local server.
// Every non-loopback browser request is fulfilled from local captured bytes;
// the test never falls back to the Internet.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require('playwright');

(async () => {
  const root = path.resolve(__dirname, '..');
  const dir = path.join(root, 'sites', 'socpk');
  const output = path.join(root, 'qa');
  fs.mkdirSync(output, { recursive: true });
  const manifest = JSON.parse(fs.readFileSync(path.join(dir, 'manifest.json'), 'utf8'));
  const audit = JSON.parse(fs.readFileSync(path.join(dir, 'audit.json'), 'utf8'));
  const exact = new Map(manifest.entries.map(e => [e.url, e]));
  const byPath = new Map(manifest.entries.map(e => [new URL(e.url).pathname, e]));
  const missing = [], consoleErrors = [], pageErrors = [], requests = [], results = [];
  const port = 18091;
  const origin = `http://127.0.0.1:${port}`;
  const server = http.createServer((req, res) => {
    const local = new URL(req.url, origin);
    const remote = local.pathname.startsWith('/_remote/')
      ? local.pathname.slice(9).replace('/', '://') + local.search
      : `https://www.socpk.com${local.pathname}${local.search}`;
    const url = new URL(remote);
    let entry = exact.get(remote) || (manifest.hostAliases.includes(url.hostname) ? byPath.get(url.pathname) : null);
    if (!entry && manifest.hostAliases.includes(url.hostname)
      && (/^\/(?:chart|category|chips)(?:\/|$)/.test(url.pathname) || url.pathname === '/')) {
      entry = byPath.get('/');
    }
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Cache-Control', 'no-store');
    if (!entry) {
      missing.push({ url: remote, method: req.method });
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('Not present in offline snapshot');
      return;
    }
    res.setHeader('Content-Type', entry.contentType);
    res.end(fs.readFileSync(path.join(dir, entry.path)));
  });
  await new Promise(resolve => server.listen(port, '127.0.0.1', resolve));
  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true,
  });
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    requests.push(url.href);
    if (url.hostname === '127.0.0.1') return route.continue();
    if (url.protocol === 'data:' || url.protocol === 'blob:') return route.continue();
    const localUrl = `${origin}/_remote/${url.protocol.slice(0, -1)}/${url.host}${url.pathname}${url.search}`;
    const response = await route.fetch({ url: localUrl });
    return route.fulfill({ response });
  });
  const page = await context.newPage();
  page.on('console', message => {
    if (message.type() === 'error') consoleErrors.push({ url: page.url(), text: message.text() });
  });
  page.on('pageerror', error => pageErrors.push({ url: page.url(), text: error.message }));
  const visit = async route => {
    await page.goto(origin + route, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.querySelector('#app')?.children.length > 0);
  };
  const screenshot = async name => page.screenshot({ path: path.join(output, `socpk-${name}.png`) });
  const text = async () => page.locator('body').innerText();
  const images = async () => page.locator('img').evaluateAll(nodes => nodes
    .filter(n => n.complete && n.naturalWidth === 0).map(n => n.src));

  await visit('/');
  await page.waitForLoadState('networkidle');
  await screenshot('home-desktop');
  results.push({ type: 'home', title: await page.title(), bodyLength: (await text()).length, brokenImages: await images() });
  // Mark the upstream's introductory tutorial as viewed via its own UI.
  for (const category of audit.categories) {
    await visit('/category/' + category);
    await page.waitForLoadState('networkidle');
    results.push({ type: 'category', category, bodyLength: (await text()).length, brokenImages: await images() });
  }
  for (const slug of audit.chartSlugs) {
    await visit('/chart/' + slug);
    await page.waitForSelector('.capture-area', { timeout: 20000 });
    await page.waitForLoadState('networkidle');
    // The original chart tutorial overlays controls on the first visit.
    const skip = page.locator('.tour-btn.skip');
    if (await skip.isVisible()) await skip.click();
    const chart = { type: 'chart', slug, title: await page.locator('.page-title').innerText(),
      bodyLength: (await text()).length, canvas: await page.locator('canvas').count(),
      svg: await page.locator('svg').count(), brokenImages: await images(), interactions: [] };
    // CSS class selection keeps this independent of the site's current locale.
    const openPanel = page.locator('.panel-button:not(.save-button)').first();
    if (await openPanel.count()) {
      await openPanel.click();
      await page.waitForSelector('.series-panel');
      chart.panelCount = await page.locator('.panel-count').innerText();
      const actions = page.locator('.panel-action');
      if (await actions.count() >= 2) {
        await actions.nth(1).click();
        chart.interactions.push({ type: 'hideAll', count: await page.locator('.panel-count').innerText() });
        await actions.nth(0).click();
        chart.interactions.push({ type: 'showAll', count: await page.locator('.panel-count').innerText() });
      }
      await page.locator('.panel-close').click();
    }
    const pills = page.locator('.suite-pills button');
    for (let i = 0; i < await pills.count(); i++) {
      await pills.nth(i).click();
      chart.interactions.push({ type: 'suite', label: await pills.nth(i).innerText() });
    }
    const fullscreen = page.locator('.fs-open');
    if (await fullscreen.count()) {
      await fullscreen.click();
      await page.waitForSelector('.fs-exit');
      await page.locator('.fs-zoom').first().click();
      chart.interactions.push({ type: 'fullscreenAndZoom', canvas: await page.locator('canvas').count() });
      await page.locator('.fs-exit').click();
      await page.waitForSelector('.fs-exit', { state: 'hidden' });
    }
    if (['mobile-soc-spec26', 'battery-life-5-0', 'laptop-gpu-efficiency'].includes(slug)) {
      await screenshot(slug + '-desktop');
    }
    results.push(chart);
  }
  await visit('/chips');
  await page.waitForSelector('.chip-card');
  await page.waitForLoadState('networkidle');
  const listCount = await page.locator('.chip-card').count();
  const chipList = { type: 'chipList', count: listCount, expected: audit.chipIds.length, brokenImages: await images() };
  await screenshot('chips-desktop');
  const filters = page.locator('.filter-row button');
  const brands = [];
  for (let i = 0; i < await filters.count(); i++) {
    await filters.nth(i).click();
    brands.push({ label: await filters.nth(i).innerText(), count: await page.locator('.chip-card').count() });
  }
  chipList.filters = brands;
  results.push(chipList);
  for (const id of audit.chipIds) {
    await visit('/chips/' + id);
    await page.waitForSelector('.chip-detail .chip-name', { timeout: 10000 });
    const detail = { type: 'chipDetail', id, name: await page.locator('.chip-detail .chip-name').innerText(),
      bodyLength: (await text()).length, brokenImages: await images() };
    results.push(detail);
  }
  // Test the site's own locale/theme controls from the common sidebar.
  await visit('/chart/mobile-soc-spec26');
  await page.waitForSelector('.capture-area');
  await page.mouse.move(5, 360);
  await page.locator('.rail').hover();
  await page.locator('.rail .toggle-btn:not(.lang-btn)').click();
  await page.waitForFunction(() => document.documentElement.dataset.theme === 'light');
  await page.waitForLoadState('networkidle');
  results.push({ type: 'theme', theme: await page.locator('html').getAttribute('data-theme'),
    brokenImages: await images() });
  await page.mouse.move(1000, 50);
  await screenshot('mobile-soc-spec26-light-desktop');
  await visit('/chart/laptop-gpu-efficiency');
  await page.waitForSelector('.capture-area');
  await page.waitForLoadState('networkidle');
  results.push({ type: 'theme', slug: 'laptop-gpu-efficiency',
    theme: await page.locator('html').getAttribute('data-theme'), brokenImages: await images() });
  await page.mouse.move(5, 360);
  await page.locator('.rail').hover();
  await page.locator('.rail .lang-btn').click();
  await page.mouse.move(1000, 50);
  results.push({ type: 'locale', title: await page.locator('.page-title').innerText(),
    htmlLang: await page.locator('html').getAttribute('lang') });
  await screenshot('laptop-gpu-efficiency-light-english-desktop');
  const buttons = await page.locator('button').evaluateAll(nodes => nodes.map(n => ({
    text: n.textContent.trim(), title: n.title, aria: n.getAttribute('aria-label'), class: n.className,
  })));
  const result = { engine: await browser.version(), capturedAt: new Date().toISOString(),
    viewport: { width: 1280, height: 720 }, networkPolicy: 'Manifest-only. External requests fulfilled from local snapshot; no Internet fallback.',
    chartCount: results.filter(r => r.type === 'chart').length,
    chipListCount: listCount, chipDetailCount: results.filter(r => r.type === 'chipDetail').length,
    missing: [...new Map(missing.map(e => [e.url, e])).values()], consoleErrors, pageErrors,
    requests: [...new Set(requests)], buttons, results };
  fs.writeFileSync(path.join(output, 'socpk-desktop.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify({ engine: result.engine, chartCount: result.chartCount,
    chipListCount: result.chipListCount, chipDetailCount: result.chipDetailCount,
    missing: result.missing, consoleErrors, pageErrors }, null, 2));
  await browser.close();
  await new Promise(resolve => server.close(resolve));
})().catch(error => { console.error(error); process.exit(1); });
