// This belongs to the Android container. Captured website files remain unchanged.
browser.webRequest.onBeforeRequest.addListener(details => {
  const url = new URL(details.url);
  if (url.hostname === '127.0.0.1' || url.hostname === 'localhost') return {};
  const source = details.originUrl || details.documentUrl || '';
  const local = source.match(/127\.0\.0\.1:(\d+)/);
  const port = local ? local[1] : OFFLINE_HOSTS[url.hostname];
  if (!port) return {cancel: true};
  return {redirectUrl: `http://127.0.0.1:${port}/_remote/${url.protocol.slice(0,-1)}/${url.host}${url.pathname}${url.search}`};
}, {urls: ['http://*/*', 'https://*/*']}, ['blocking']);
