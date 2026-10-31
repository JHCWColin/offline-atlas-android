/* ModelDial GA4. Starts automatically; explicit opt-outs take priority.
   Enhanced measurement is disabled in the web data stream. */
function modeldialAnalytics() {
  'use strict';
  if (window.__modeldialGA) return;
  if (navigator.webdriver) return;
  window.__modeldialGA = true;
  const id = 'G-Z6KHRVMHHG';
  const key = 'modeldial_ga_consent_v1';
  const en = () => /^\/en(?:\/|$)/.test(location.pathname);
  const restricted = navigator.doNotTrack === '1' || Boolean(navigator.globalPrivacyControl);
  let optedOut = false;
  try { optedOut = JSON.parse(localStorage.getItem(key) || 'null')?.value === 'denied'; } catch { /* Optional storage. */ }
  const testTrafficKey = 'modeldial_analytics_test_v1';
  let testTraffic = false;
  function isTestTraffic() {
    const choice = new URLSearchParams(location.search).get('md_test');
    try {
      if (choice === '1' || choice === '0') sessionStorage.setItem(testTrafficKey, choice);
      testTraffic = sessionStorage.getItem(testTrafficKey) === '1';
    } catch { if (choice === '1' || choice === '0') testTraffic = choice === '1'; }
    return testTraffic;
  }
  const allowed = () => !isTestTraffic() && !restricted && navigator.doNotTrack !== '1' && !navigator.globalPrivacyControl && !optedOut;
  window['ga-disable-' + id] = !allowed();
  let enabled = false;
  let started = false;
  let lastPath = null;
  let previous = '';
  let panel;
  let viewTimer;
  const publicPath = () => !/^\/(?:en\/)?(?:api|admin|studio|_next)(?:\/|$)/.test(location.pathname);
  const cleanURL = (value) => {
    try { const url = new URL(value); return url.origin + url.pathname; } catch { return ''; }
  };
  const gtag = function () { window.dataLayer.push(arguments); };
  const campaignMedia = { wechat: 'social', wecom: 'social', x: 'social', zhihu: 'social', xiaohongshu: 'social', bilibili: 'social', github: 'referral', reddit: 'social', newsletter: 'email', partner: 'referral', share: 'referral' };
  function campaign() {
    const params = new URLSearchParams(location.search);
    const source = [params.get('md_source'), params.get('utm_source')].find(value => Object.hasOwn(campaignMedia, value));
    return source ? { campaign_source: source, campaign_medium: campaignMedia[source], campaign_name: source === 'share' ? 'site_share' : 'site_distribution' } : {};
  }
  const businessEvents = new Set(['core_entry_click', 'score_detail_view', 'community_open', 'community_qr_view', 'community_qr_error', 'subscription_view_change', 'subscription_budget_change', 'model_assistant_view', 'model_assistant_open', 'model_assistant_result', 'model_assistant_action', 'model_search', 'ranking_change', 'comparison_select', 'comparison_open', 'share_open', 'comparison_ready', 'share_generate_attempt', 'share_generate_success', 'share_generate_failure', 'share_copy_attempt', 'share_copy_success', 'share_copy_failure', 'share_download_start', 'share_native_attempt', 'share_native_resolved', 'share_native_cancel', 'share_native_failure', 'share_link_attempt', 'share_link_success', 'share_link_failure', 'app_download_click', 'subscription_entry_click', 'subscription_filter', 'subscription_search', 'subscription_period_change', 'subscription_compare_select', 'subscription_scores_click', 'subscription_calculator_view', 'subscription_calculator_open', 'subscription_calculator_mode', 'subscription_calculator_change', 'subscription_calculator_result', 'subscription_calculator_scores_click', 'subscription_calculator_compare', 'subscription_calculator_switch', 'subscription_calculator_undo', 'subscription_calculator_basis', 'subscription_calculator_copy_attempt', 'subscription_calculator_copy_success', 'subscription_calculator_copy_failure', 'pareto_open', 'pareto_filter', 'pareto_select', 'pareto_compare', 'model_efforts_open', 'comparison_change', 'content_expand', 'contact_entry_click', 'contact_mail_click', 'contact_copy_attempt', 'contact_copy_success', 'contact_copy_failure']);
  businessEvents.add('arena_entry_click');
  const pageGroups = ['home', 'radar', 'method', 'guides', 'data_license', 'model', 'compare', 'datasets', 'subscriptions', 'download', 'contact', 'agent'];
  const entryChannels = ['direct', 'internal', 'search', 'social', 'external', ...Object.keys(campaignMedia)];
  function businessEvent(record) {
    if (!enabled || !allowed() || !publicPath() || !record || !businessEvents.has(record.event)) return;
    // Only replay short-lived events from this document. No persistent queue or retries.
    if (!Number.isFinite(record.at) || Date.now() - record.at > 30_000 || record.at > Date.now()) return;
    const source = record.params;
    if (!source || !pageGroups.includes(source.page_group)) return;
    let page;
    try { page = new URL(source.page_location); } catch { return; }
    if (page.origin !== location.origin || page.pathname !== location.pathname) return;
    if (record.event.startsWith('model_assistant_') && !['/', '/radar', '/radar/'].includes(page.pathname)) return;
    pageView();
    const params = { send_to: id, page_location: page.origin + page.pathname, page_group: source.page_group };
    if (record.event === 'arena_entry_click') params.site_section = 'website';
    // Rebuild the payload rather than forwarding arbitrary UI or URL values.
    if (['en', 'zh-CN'].includes(source.site_locale)) params.site_locale = source.site_locale;
    if (entryChannels.includes(source.entry_channel)) params.entry_channel = source.entry_channel;
    if (['all', 'OpenAI', 'Claude', 'Grok', 'Google', 'GLM', 'Kimi'].includes(source.quota_provider)) params.quota_provider = source.quota_provider;
    if (['fiveHours', 'week', 'month'].includes(source.quota_period)) params.quota_period = source.quota_period;
    if (['single', 'group', 'comparison'].includes(source.share_scope)) params.share_scope = source.share_scope;
    const enums = {
      arena_entry: ['header', 'mobile_menu'],
      entry_source: ['hero', 'new_models', 'provider_leaders', 'home_leader', 'home_leaderboard', 'generation', 'home_chart'],
      destination_group: ['radar', 'model', 'compare'],
      community_placement: ['header', 'footer'],
      community_trigger: ['hover', 'click', 'keyboard'],
      community_status: ['expired', 'unavailable', 'image_error'],
      subscription_view: ['insights', 'catalog', 'calculator'],
      budget_currency: ['USD', 'CNY'],
      budget_scope: ['near', 'within'],
      budget_metric: ['tokens', 'dollars'],
      budget_band: ['invalid', 'under_20', '20_99', '100_199', '200_499', '500_plus'],
      budget_status: ['ready', 'no_results', 'invalid_input'],
      resource_unit: ['cost', 'tokens'],
      chart_region: ['all', 'domestic', 'overseas', 'unknown'],
      frontier_visible: ['yes', 'no'],
      assistant_flow: ['discover', 'shortlist', 'replace', 'consult', 'team'],
      assistant_status: ['with_configurations', 'without_configurations'],
      assistant_action: ['scores', 'compare'],
      contact_entry: ['header', 'mobile_menu', 'footer'],
      quota_entry: ['ranking', 'ranking_toolbar', 'ranking_selection', 'ranking_picker', 'model_detail', 'header', 'mobile_menu'],
      content_type: ['ranking', 'model', 'comparison', 'subscription'],
      share_provider: ['OpenAI', 'Claude', 'Grok', 'Google', 'GLM', 'Kimi', 'mixed'],
      search_surface: ['ranking', 'catalog', 'compare_picker'],
      evaluation_axis: ['overall', 'backend', 'frontend', 'knowledge', 'aesthetic', 'maintainability'],
      ranking_mode: ['capability', 'deep', 'balanced', 'fast'],
      change_type: ['axis', 'preference', 'provider', 'sort', 'quality_reference', 'quality_limit', 'include_cost', 'view', 'reset'],
      selection_action: ['add', 'remove', 'clear'],
      comparison_surface: ['page', 'drawer', 'picker'],
      analysis_feature: ['pareto', 'model_efforts', 'comparison_evidence', 'task_cost'],
      analysis_action: ['score_filter', 'cost_filter', 'reset', 'frontier', 'all', 'point', 'add', 'remove', 'scores', 'radar', 'axis', 'basis', 'effort', 'baseline', 'resources', 'details', 'unit', 'region', 'open'],
      calculator_mode: ['work', 'remaining', 'plans'],
      calculator_action: ['mode', 'plan', 'model', 'effort', 'remaining', 'demand', 'period', 'switch', 'undo', 'reset', 'recover'],
      calculator_status: ['ready', 'invalid_input', 'no_period_data', 'no_work_data', 'no_plan'],
    };
    for (const [key, values] of Object.entries(enums)) {
      if (values.includes(source[key])) params[key] = source[key];
    }
    if ((record.event === 'share_native_failure' || record.event === 'share_generate_failure') && ['permission', 'unsupported', 'invalid_file', 'unavailable', 'encoding', 'timeout', 'unknown'].includes(source.share_failure_reason)) {
      params.share_failure_reason = source.share_failure_reason;
    }
    if (record.event === 'share_generate_failure' && ['canvas', 'draw', 'qr', 'encode', 'preview'].includes(source.share_failure_stage)) {
      params.share_failure_stage = source.share_failure_stage;
    }
    for (const [key, max] of [['result_count', 1000], ['selected_count', (record.event.startsWith('comparison_') || record.event === 'pareto_compare' || (record.event.startsWith('share_') && source.content_type === 'comparison')) ? 5 : 3]]) {
      if (Number.isInteger(source[key]) && source[key] >= 0 && source[key] <= max) params[key] = source[key];
    }
    gtag('event', record.event, params);
  }
  window.__modeldialTrackGA = businessEvent;
  function pageView() {
    if (!enabled || !allowed() || !publicPath() || lastPath === location.pathname) return;
    const title = document.title.trim();
    // Next can temporarily clear the title while committing a navigation.
    if (!title) return;
    const page = location.origin + location.pathname;
    gtag('set', { page_location: page, page_title: title });
    gtag('event', 'page_view', {
      send_to: id,
      page_location: page,
      page_title: title,
      page_referrer: previous || cleanURL(document.referrer),
    });
    previous = page;
    lastPath = location.pathname;
  }
  function schedulePageView() {
    clearTimeout(viewTimer);
    viewTimer = setTimeout(pageView, 100);
  }
  function start() {
    if (!allowed() || !publicPath() || !['modeldial.com', 'www.modeldial.com'].includes(location.hostname)) return;
    enabled = true;
    window['ga-disable-' + id] = false;
    if (!started) {
      started = true;
      window.dataLayer = window.dataLayer || [];
      gtag('consent', 'default', {
        analytics_storage: 'granted', ad_storage: 'denied',
        ad_user_data: 'denied', ad_personalization: 'denied',
      });
      gtag('js', new Date());
      gtag('config', id, {
        send_page_view: false,
        allow_google_signals: false,
        allow_ad_personalization_signals: false,
        page_location: location.origin + location.pathname,
        page_referrer: cleanURL(document.referrer),
        ...campaign(),
      });
      const script = document.createElement('script');
      script.async = true;
      script.src = 'https://www.googletagmanager.com/gtag/js?id=' + id;
      document.head.appendChild(script);
    } else {
      gtag('consent', 'update', { analytics_storage: 'granted' });
    }
    pageView();
  }
  function choose(value) {
    optedOut = value === 'denied';
    try { localStorage.setItem(key, JSON.stringify({ value, at: Date.now() })); } catch { /* Optional storage. */ }
    if (panel?.open) panel.close();
    if (allowed()) start();
    else {
      enabled = false;
      window.__modeldialGAQueue = [];
      window['ga-disable-' + id] = true;
      if (started) gtag('consent', 'update', { analytics_storage: 'denied' });
      document.cookie.split(';').forEach((cookie) => {
        const name = cookie.split('=')[0].trim();
        if (!/^_ga(?:_|$)/.test(name)) return;
        ['', '; domain=modeldial.com', '; domain=.modeldial.com'].forEach((domain) => {
          document.cookie = name + '=; Max-Age=0; path=/' + domain + '; SameSite=Lax; Secure';
        });
      });
    }
  }
  function show() {
    if (panel && panel.isConnected) return;
    panel = document.createElement('dialog');
    panel.className = 'md-ga-panel';
    panel.setAttribute('aria-labelledby', 'md-ga-title');
    panel.setAttribute('aria-describedby', 'md-ga-description');
    const heading = document.createElement('h2');
    heading.id = 'md-ga-title';
    heading.textContent = en() ? 'Privacy & analytics' : '隐私与访问统计';
    panel.appendChild(heading);
    const text = document.createElement('p');
    text.id = 'md-ga-description';
    text.textContent = en()
      ? 'Google Analytics uses cookies to distinguish browsers and sessions. You can turn off visit analytics at any time without affecting site features.'
      : 'Google Analytics 使用 Cookie 区分浏览器和会话。你可以随时关闭访问统计，网站功能不受影响。';
    panel.appendChild(text);
    const status = document.createElement('p');
    status.className = 'md-ga-status';
    status.textContent = restricted
      ? (en() ? 'Analytics is off because your browser requests not to be tracked.' : '当前浏览器已请求不跟踪，访问统计保持关闭。')
      : (en() ? 'Visit analytics: ' + (allowed() ? 'On' : 'Off') : '访问统计：' + (allowed() ? '已开启' : '已关闭'));
    panel.appendChild(status);
    const link = document.createElement('a');
    link.href = 'https://policies.google.com/technologies/partner-sites';
    link.target = '_blank'; link.rel = 'noopener noreferrer';
    link.textContent = en() ? 'How Google uses data' : 'Google 如何使用数据';
    panel.appendChild(link);
    const actions = document.createElement('div');
    if (!restricted) {
      const value = allowed() ? 'denied' : 'granted';
      const button = document.createElement('button');
      button.type = 'button'; button.textContent = en()
        ? (allowed() ? 'Turn off analytics' : 'Turn on analytics')
        : (allowed() ? '关闭访问统计' : '开启访问统计');
      button.addEventListener('click', () => choose(value)); actions.appendChild(button);
    }
    const close = document.createElement('button');
    close.type = 'button'; close.textContent = en() ? 'Close' : '关闭';
    close.addEventListener('click', () => panel.close());
    actions.prepend(close);
    panel.appendChild(actions); document.body.appendChild(panel);
    panel.addEventListener('close', () => { panel.remove(); opener?.focus(); });
    panel.showModal();
    close.focus();
  }
  const style = document.createElement('style');
  style.textContent = '.md-ga-panel{width:min(480px,calc(100vw - 32px));max-height:calc(100dvh - 32px);box-sizing:border-box;margin:auto;padding:24px;background:#fff;color:#202124;border:1px solid #e9eaec;border-radius:16px;box-shadow:0 16px 56px #20212420;font:inherit;font-size:14px;line-height:1.65}.md-ga-panel::backdrop{background:#20212455}.md-ga-panel h2{margin:0 0 16px;font-size:20px;font-weight:600}.md-ga-panel p{margin:0 0 14px;color:#70747b}.md-ga-panel .md-ga-status{color:#202124}.md-ga-panel a{color:#355fdd}.md-ga-panel>div{display:flex;justify-content:flex-end;flex-wrap:wrap;gap:8px;margin-top:24px}.md-ga-panel button{padding:8px 14px;border:1px solid #e9eaec;border-radius:8px;background:#fff;color:#202124;cursor:pointer;font:inherit}.md-ga-panel button:last-child:not(:first-child){background:#202124;color:#fff}.md-ga-footer{box-sizing:border-box;max-width:1240px;margin:0 auto;padding:24px;color:#70747b;font:inherit;font-size:12px;line-height:1.5}.md-ga-settings{border:0;padding:0;background:none;color:inherit;font:inherit;font-size:12px;cursor:pointer}.md-ga-settings:hover{color:#355fdd}.overview-root footer nav .md-ga-settings{font:inherit;font-size:12px;line-height:inherit;padding:8px 13px;border-radius:8px;color:var(--muted);white-space:nowrap}.overview-root footer nav .md-ga-settings:hover{color:var(--blue)}@media(max-width:760px){.overview-root footer nav .md-ga-settings{font-size:11px;padding:5px 7px}}.md-ga-panel button:focus-visible,.md-ga-settings:focus-visible{outline:2px solid #355fdd;outline-offset:3px}';
  document.head.appendChild(style);
  function sourceGroup(path) {
    const groups = { '/': 'home', '/radar': 'radar', '/method': 'method', '/guides': 'guides', '/data-license': 'data_license', '/datasets': 'datasets', '/download': 'download', '/contact': 'contact', '/agent': 'agent' };
    return groups[path] || (/^\/models(?:\/|$)/.test(path) ? 'model' : /^\/compare(?:\/|$)/.test(path) ? 'compare' : /^\/subscriptions(?:\/|$)/.test(path) ? 'subscriptions' : null);
  }
  // Anchors are measured in capture phase before either navigation system changes the route.
  function coreEntry(event) {
    if (event.type === 'auxclick' && event.button !== 1) return;
    const path = location.pathname.replace(/^\/en(?=\/|$)/, '').replace(/\/$/, '') || '/';
    if (path !== '/') return;
    const link = event.target instanceof Element ? event.target.closest('a[href]') : null;
    if (!link) return;
    let destination;
    try { destination = new URL(link.getAttribute('href'), location.href); } catch { return; }
    if (destination.origin !== location.origin) return;
    const destPath = destination.pathname.replace(/^\/en(?=\/|$)/, '').replace(/\/$/, '') || '/';
    const group = sourceGroup(destPath === '/' && ['#radar', '#compare'].includes(destination.hash) ? '/' + destination.hash.slice(1) : destPath);
    if (!['radar', 'model', 'compare'].includes(group)) return;
    const placement = [['.home-leader', 'home_leader'], ['.home-hero', 'hero'], ['.hero-releases', 'new_models'], ['.home-providers', 'provider_leaders'], ['.ranking-section', 'home_leaderboard'], ['.home-generations', 'generation'], ['.home-cost', 'home_chart']].find(([selector]) => link.closest(selector));
    if (!placement) return;
    businessEvent({ event: 'core_entry_click', at: Date.now(), params: { page_location: location.origin + location.pathname, page_group: 'home', site_locale: en() ? 'en' : 'zh-CN', entry_source: placement[1], destination_group: group } });
  }
  document.addEventListener('click', coreEntry, { capture: true });
  document.addEventListener('auxclick', coreEntry, { capture: true });
  // Both header implementations use the same capture listener before leaving this document.
  function arenaEntry(event) {
    if ((event.type === 'auxclick' && event.button !== 1) || (event.type === 'click' && event.button !== 0)) return;
    const link = event.target instanceof Element ? event.target.closest('a[data-arena-entry]') : null;
    if (!link) return;
    const entry = link.getAttribute('data-arena-entry');
    if (!['header', 'mobile_menu'].includes(entry)) return;
    let destination;
    try { destination = new URL(link.getAttribute('href'), location.href); } catch { return; }
    if (destination.origin !== 'https://arena.modeldial.com' || destination.pathname !== '/') return;
    const path = location.pathname.replace(/^\/en(?=\/|$)/, '').replace(/\/$/, '') || '/';
    const group = sourceGroup(path);
    if (!group) return;
    businessEvent({ event: 'arena_entry_click', at: Date.now(), params: {
      page_location: location.origin + location.pathname, page_group: group,
      site_locale: en() ? 'en' : 'zh-CN', arena_entry: entry,
    } });
  }
  document.addEventListener('click', arenaEntry, { capture: true });
  document.addEventListener('auxclick', arenaEntry, { capture: true });
  // Capture the source route before client navigation; one listener serves both header systems.
  function contactEntry(event) {
    const link = event.target instanceof Element ? event.target.closest('a[data-contact-entry]') : null;
    if (!link) return;
    const entry = link.getAttribute('data-contact-entry');
    if (!['header', 'mobile_menu', 'footer'].includes(entry)) return;
    let destination;
    try { destination = new URL(link.getAttribute('href'), location.href); } catch { return; }
    if (destination.origin !== location.origin || !/^\/(?:en\/)?contact\/?$/.test(destination.pathname)) return;
    const path = location.pathname.replace(/^\/en(?=\/|$)/, '').replace(/\/$/, '') || '/';
    const groups = { '/': 'home', '/radar': 'radar', '/method': 'method', '/guides': 'guides', '/data-license': 'data_license', '/datasets': 'datasets', '/download': 'download', '/contact': 'contact' };
    const group = groups[path] || (/^\/models(?:\/|$)/.test(path) ? 'model' : /^\/compare(?:\/|$)/.test(path) ? 'compare' : /^\/subscriptions(?:\/|$)/.test(path) ? 'subscriptions' : null);
    if (!group) return;
    businessEvent({ event: 'contact_entry_click', at: Date.now(), params: {
      page_location: location.origin + location.pathname, page_group: group,
      site_locale: en() ? 'en' : 'zh-CN', contact_entry: entry,
    } });
  }
  document.addEventListener('click', contactEntry, { capture: true });
  // Entry intent only: arrival and meaningful use are separate page/calculator events.
  function quotaEntry(event) {
    const link = event.target instanceof Element ? event.target.closest('a[data-quota-entry]') : null;
    if (!link) return;
    const entry = link.getAttribute('data-quota-entry');
    if (!['ranking', 'ranking_toolbar', 'ranking_selection', 'ranking_picker', 'model_detail', 'header', 'mobile_menu'].includes(entry)) return;
    let destination;
    try { destination = new URL(link.getAttribute('href'), location.href); } catch { return; }
    if (destination.origin !== location.origin || !/^\/(?:en\/)?subscriptions(?:\/|$)/.test(destination.pathname)) return;
    const path = location.pathname.replace(/^\/en(?=\/|$)/, '').replace(/\/$/, '') || '/';
    const group = sourceGroup(path);
    if (!group) return;
    businessEvent({ event: 'subscription_entry_click', at: Date.now(), params: {
      page_location: location.origin + location.pathname, page_group: group,
      site_locale: en() ? 'en' : 'zh-CN', quota_entry: entry,
      quota_provider: destination.searchParams.get('provider') || 'all',
      evaluation_axis: new URLSearchParams(location.search).get('axis') || 'overall',
    } });
  }
  document.addEventListener('click', quotaEntry, { capture: true });

  let opener;
  document.addEventListener('click', (event) => {
    const settings = event.target instanceof Element ? event.target.closest('.md-ga-settings') : null;
    if (!settings) return;
    opener = settings;
    show();
  });
  new MutationObserver(schedulePageView).observe(document.head, { childList: true, subtree: true, characterData: true });
  // Default-on is site configuration, not a fabricated record of user consent.
  start();
  const buffered = window.__modeldialGAQueue || [];
  window.__modeldialGAQueue = [];
  buffered.forEach(businessEvent);
  window.addEventListener('storage', (event) => {
    if (event.key !== key && event.key !== null) return;
    try { optedOut = JSON.parse(localStorage.getItem(key) || 'null')?.value === 'denied'; } catch { return; }
    if (allowed()) start();
    else {
      enabled = false;
      window.__modeldialGAQueue = [];
      window['ga-disable-' + id] = true;
      if (started) gtag('consent', 'update', { analytics_storage: 'denied' });
    }
  });

  const changed = () => setTimeout(() => {
    if (!allowed()) {
      enabled = false;
      window.__modeldialGAQueue = [];
      window['ga-disable-' + id] = true;
      if (started) gtag('consent', 'update', { analytics_storage: 'denied' });
    } else if (!enabled) start();
    else schedulePageView();
  }, 0);
  ['pushState', 'replaceState'].forEach((method) => {
    const original = history[method];
    history[method] = function () { const result = original.apply(this, arguments); changed(); return result; };
  });
  window.addEventListener('popstate', changed);
}
if (document.body) modeldialAnalytics();
else document.addEventListener('DOMContentLoaded', modeldialAnalytics, { once: true });
