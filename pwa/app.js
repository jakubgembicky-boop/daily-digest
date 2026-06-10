/* Daily Digest PWA — app.js
   Vanilla JS only. No frameworks, no CDN, no external fonts.
   localStorage usage: ONLY for analytics events (key: digest_analytics).
*/

'use strict';

// ── Constants ──────────────────────────────────────────────────────────────
const ANALYTICS_KEY  = 'digest_analytics';
const DIGEST_LATEST  = 'data/digest.json';
const DIGEST_ARCHIVE = date => `digests/${date}.json`;
const MARKET_DROP_ALERT = -1.5;   // % move that earns the "!" alert

// Category metadata (mirrors config.py CATEGORIES — kept in sync manually)
const CAT_META = {
  slovakia: { label:'Slovakia',          emoji:'🇸🇰', color:'#0080C7' },
  czechia:  { label:'Czechia',           emoji:'🇨🇿', color:'#B45309' },
  europe:   { label:'Europe & Defence',  emoji:'🇪🇺', color:'#003399' },
  war:      { label:'War & Conflict',    emoji:'🔴',  color:'#CC2222' },
  sport:    { label:'Sport',             emoji:'🏆',  color:'#1DB954' },
  global:   { label:'Global',           emoji:'🌍',  color:'#F59E0B' },
  tech:     { label:'Tech',              emoji:'💻',  color:'#7C3AED' },
  ai:       { label:'AI',                emoji:'🤖',  color:'#8B5CF6' },
  economy:  { label:'Economy & Finance', emoji:'📈',  color:'#6B7280' },
  hr:       { label:'HR & Management',   emoji:'👥',  color:'#0891B2' },
  health:   { label:'Health & Lifestyle',emoji:'🏃',  color:'#059669' },
  _wildcard:{ label:'Trending',          emoji:'🌐',  color:'#EC4899' },
};
const CAT_ORDER = [
  'slovakia','czechia','europe','war','sport','global',
  'tech','ai','economy','hr','health',
];

// ── State ──────────────────────────────────────────────────────────────────
let digest       = null;
let currentDate  = null;
let currentView  = 'day';    // 'day' | 'grouped'
let activeFilters = new Set();
let readSet      = new Set();

// Stable story ID: hash of primary URL (avoids depending on Claude generating IDs)
function storyId(story) {
  const key = story?.primary?.url || story?.title || Math.random().toString();
  let h = 0;
  for (let i = 0; i < key.length; i++) {
    h = (Math.imul(31, h) + key.charCodeAt(i)) | 0;
  }
  return 'S' + Math.abs(h).toString(36);
}

// ── Analytics ──────────────────────────────────────────────────────────────
const Analytics = {
  load() {
    try { return JSON.parse(localStorage.getItem(ANALYTICS_KEY) || '[]'); }
    catch { return []; }
  },
  save(events) {
    try { localStorage.setItem(ANALYTICS_KEY, JSON.stringify(events)); }
    catch {}
  },
  push(event) {
    const events = this.load();
    events.push({ ...event, ts: Date.now() });
    const cutoff = Date.now() - 180 * 86400_000;
    this.save(events.filter(e => e.ts > cutoff));
  },
  logDigestOpen()                  { this.push({ type:'digest_open' }); },
  logArticleOpen(story, source)    {
    this.push({
      type: 'article_open',
      article_id: storyId(story),
      category:   story.category,
      source:     source?.source || '',
      paid:       source?.paid || false,
    });
  },
  logFeedback(id, category, vote) {
    this.push({ type:'feedback', article_id:id, category, vote });
  },
  compute() {
    const events = this.load();
    const now = Date.now(), d30 = now - 30*86400_000, d24 = now - 86400_000;

    const openDays = new Set(
      events.filter(e => e.type === 'digest_open')
            .map(e => new Date(e.ts).toDateString())
    );
    let streak = 0;
    const today = new Date();
    for (let i = 0; i < 365; i++) {
      const d = new Date(today); d.setDate(d.getDate() - i);
      if (openDays.has(d.toDateString())) streak++; else break;
    }

    const opensToday = events.filter(e => e.type === 'article_open' && e.ts > d24).length;
    const opens30    = events.filter(e => e.type === 'article_open' && e.ts > d30);
    const avgPerDay  = (opens30.length / 30).toFixed(1);

    const srcCount = {};
    opens30.forEach(e => { srcCount[e.source] = (srcCount[e.source]||0) + 1; });
    const favSource = Object.entries(srcCount).sort((a,b)=>b[1]-a[1])[0]?.[0] || '—';

    const monthStart = new Date(); monthStart.setDate(1); monthStart.setHours(0,0,0,0);
    const catCount = {};
    events.filter(e => e.type === 'article_open' && e.ts > monthStart.getTime())
          .forEach(e => { catCount[e.category] = (catCount[e.category]||0)+1; });

    return { streak, opensToday, avgPerDay, favSource, catCount };
  },
};

// ── Digest loader ──────────────────────────────────────────────────────────
async function loadDigest(date = null) {
  const url = date ? DIGEST_ARCHIVE(date) : DIGEST_LATEST;
  const res = await fetch(url + '?_=' + Date.now());
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── Calendar ───────────────────────────────────────────────────────────────
function buildCalendar() {
  const strip = document.getElementById('calendar-scroll');
  strip.innerHTML = '';
  const today = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today); d.setDate(d.getDate() - i);
    const iso = d.toISOString().slice(0, 10);
    const days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    const btn = document.createElement('button');
    btn.className = 'cal-day' + (i === 0 ? ' today' : '');
    if (iso === currentDate) btn.classList.add('selected');
    btn.dataset.date = iso;
    btn.innerHTML = `<span class="day-name">${days[d.getDay()]}</span>
                     <span class="day-num">${d.getDate()}</span>`;
    btn.addEventListener('click', () => switchDate(iso));
    strip.appendChild(btn);
  }
  requestAnimationFrame(() => { strip.scrollLeft = strip.scrollWidth; });
}

async function switchDate(date) {
  if (date === currentDate) return;
  showLoading(true);
  try {
    digest = await loadDigest(date);
    currentDate = date;
    buildCalendar();
    renderArticles();
  } catch { showToast('No digest for ' + date); }
  finally  { showLoading(false); }
}

// ── Category filters ───────────────────────────────────────────────────────
function buildFilters() {
  const ctrl = document.getElementById('view-controls');
  ctrl.querySelectorAll('.cat-filter,.filter-sep').forEach(el => {
    if (!el.dataset.view) el.remove();
  });
  if (!digest) return;
  const sep = document.createElement('div');
  sep.className = 'filter-sep';
  ctrl.appendChild(sep);

  CAT_ORDER.filter(c => digest.categories?.[c]).forEach(cat => {
    const meta  = CAT_META[cat] || {};
    const btn   = document.createElement('button');
    btn.className = 'cat-filter' + (activeFilters.has(cat) ? ' active' : '');
    btn.dataset.cat = cat;
    btn.style.setProperty('--cat-active', meta.color || '#888');
    if (activeFilters.has(cat)) btn.style.background = meta.color;
    btn.innerHTML = `<span class="filter-dot" style="background:${meta.color||'#888'}"></span>
                     ${meta.emoji||''} ${meta.label||cat}`;
    btn.addEventListener('click', () => {
      if (activeFilters.has(cat)) activeFilters.delete(cat);
      else activeFilters.add(cat);
      buildFilters();
      renderCurrentView();
    });
    ctrl.appendChild(btn);
  });
}

function visibleStories() {
  if (!digest) return [];
  const all = [];
  CAT_ORDER.forEach(cat => {
    if (activeFilters.size > 0 && !activeFilters.has(cat)) return;
    const block = digest.categories?.[cat];
    if (!block) return;
    (block.stories || []).forEach(s => all.push({ ...s, category: cat }));
  });
  // Wildcard always appended in flat view if no filter active
  if (digest.wildcard && activeFilters.size === 0) {
    all.push({ ...digest.wildcard, category: '_wildcard' });
  }
  return all;
}

// ── Card rendering ─────────────────────────────────────────────────────────
function makeCard(story) {
  const cat     = story.category || 'global';
  const meta    = CAT_META[cat] || {};
  const color   = meta.color || '#888';
  const sid     = storyId(story);
  const isRead  = readSet.has(sid);
  const primary = story.primary   || {};
  const secondary = story.secondary || null;
  const isWild  = cat === '_wildcard';

  const card = document.createElement('div');
  card.className = 'story-card' + (isRead ? ' read' : '') + (isWild ? ' card-wildcard' : '');
  card.style.setProperty('--cat-color', color);
  card.dataset.id = sid;

  // Badges row
  const trendBadge = story.trending
    ? `<span class="badge badge-trending">🔥 Trending</span>` : '';
  const wildcardBadge = isWild
    ? `<span class="badge badge-wildcard">🌐 Outside categories</span>` : '';

  // Source meta
  const paidIcon = primary.paid
    ? `<span class="paid-icon" title="Premium source">💎</span>` : '';
  const sourceLine = primary.source
    ? `<div class="card-source-meta">${escHtml(primary.source)}${paidIcon}</div>` : '';

  // Why line (wildcard only)
  const whyLine = isWild && story.why
    ? `<div class="card-why">${escHtml(story.why)}</div>` : '';

  // Trending score (wildcard)
  const trendScore = isWild && story.trending_score
    ? `<div class="card-trend-score">Reddit: ${story.trending_score.toLocaleString()} upvotes</div>` : '';

  card.innerHTML = `
    <div class="card-body">
      <div class="card-cat-row">
        <div class="card-cat-dot"></div>
        <span class="card-cat-label">${escHtml(meta.label || cat)}</span>
        ${trendBadge}${wildcardBadge}
      </div>
      <div class="card-title">${escHtml(story.title)}</div>
      <div class="card-summary">${escHtml(story.summary || '')}</div>
      ${whyLine}${trendScore}${sourceLine}
    </div>
    <div class="card-actions">
      <div class="card-action-left">
        <button class="card-open-btn" data-action="open">Read ↗</button>
        ${secondary ? `<button class="card-secondary-btn" data-action="secondary"
            title="Also: ${escHtml(secondary.source)}">${escHtml(secondary.source)} ↗</button>` : ''}
      </div>
      <div class="card-like-row">
        <button class="like-btn"    data-action="like"    title="More like this">👍</button>
        <button class="dislike-btn" data-action="dislike" title="Less like this">👎</button>
      </div>
    </div>`;

  function markRead() {
    if (readSet.has(sid)) return;
    readSet.add(sid);
    card.classList.add('read');
    sinkReadCards();
  }

  card.addEventListener('click', e => {
    const action = e.target.closest('[data-action]')?.dataset.action;

    if (action === 'like' || action === 'dislike') {
      e.target.closest('[data-action]').classList.toggle('voted');
      Analytics.logFeedback(sid, cat, action);
      showToast(action === 'like' ? 'More like this 👍' : 'Less like this 👎');
      return;
    }
    if (action === 'secondary') {
      if (secondary?.url) window.open(secondary.url, '_blank', 'noopener');
      Analytics.logArticleOpen(story, secondary);
      return; // secondary opens do NOT mark as read
    }
    // Tapping the card body or "Read ↗" → open primary
    if (primary.url) window.open(primary.url, '_blank', 'noopener');
    Analytics.logArticleOpen(story, primary);
    markRead();
  });

  return card;
}

function sinkReadCards() {
  const grid = document.getElementById('cards-grid');
  if (!grid) return;
  const cards  = [...grid.querySelectorAll('.story-card')];
  const unread = cards.filter(c => !c.classList.contains('read'));
  const read   = cards.filter(c =>  c.classList.contains('read'));
  unread.forEach(c => grid.appendChild(c));
  read.forEach(c   => grid.appendChild(c));
}

// ── Day view (flat shuffled grid) ──────────────────────────────────────────
function renderDayView() {
  const grid = document.getElementById('cards-grid');
  grid.innerHTML = '';
  document.getElementById('day-view').style.display          = '';
  document.getElementById('week-month-view').style.display   = 'none';

  const stories = visibleStories();
  if (!stories.length) {
    grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">
      <div class="empty-icon">📭</div>
      <p>No stories match the current filter</p></div>`;
    renderWidgets();
    return;
  }

  // Shuffle — keeps the browse experience fresh
  const shuffled = [...stories].sort(() => Math.random() - 0.5);
  shuffled.forEach(s => grid.appendChild(makeCard(s)));
  sinkReadCards();
  renderWidgets();
}

// ── Grouped view (by category, with summaries) ─────────────────────────────
function renderGroupedView() {
  const container = document.getElementById('week-month-view');
  container.innerHTML = '';
  document.getElementById('day-view').style.display          = 'none';
  document.getElementById('week-month-view').style.display   = '';
  if (!digest) return;

  const cats = CAT_ORDER.filter(c => {
    if (activeFilters.size > 0 && !activeFilters.has(c)) return false;
    return (digest.categories?.[c]?.stories?.length || 0) > 0;
  });

  cats.forEach(cat => {
    const block = digest.categories[cat];
    const meta  = CAT_META[cat] || {};
    const color = meta.color || '#888';
    const n     = block.stories?.length || 0;

    const section = document.createElement('div');
    section.className = 'cat-section';

    const summaryHtml = block.summary
      ? `<div class="cat-summary">${escHtml(block.summary)}</div>` : '';

    section.innerHTML = `
      <div class="cat-section-header">
        <div class="cat-section-dot" style="background:${color}"></div>
        <div class="cat-section-title">${meta.emoji||''} ${escHtml(meta.label||cat)}</div>
        <div class="cat-section-count">${n} ${n===1?'story':'stories'}</div>
      </div>
      ${summaryHtml}
      <div class="cat-section-grid"></div>`;

    const grid = section.querySelector('.cat-section-grid');
    (block.stories || []).forEach(s => grid.appendChild(makeCard({ ...s, category: cat })));
    container.appendChild(section);
  });

  // Wildcard at the very bottom if present
  if (digest.wildcard && activeFilters.size === 0) {
    const wc = document.createElement('div');
    wc.className = 'cat-section';
    wc.innerHTML = `
      <div class="cat-section-header">
        <div class="cat-section-dot" style="background:#EC4899"></div>
        <div class="cat-section-title">🌐 Trending</div>
        <div class="cat-section-count">1 story</div>
      </div>
      <div class="cat-section-grid"></div>`;
    wc.querySelector('.cat-section-grid')
      .appendChild(makeCard({ ...digest.wildcard, category: '_wildcard' }));
    container.appendChild(wc);
  }
}

function renderCurrentView() {
  if (currentView === 'day') renderDayView();
  else renderGroupedView();
}

// ── Widget rendering (once, at bottom, no duplicates) ─────────────────────
function renderWidgets() {
  const dayView = document.getElementById('day-view');
  dayView.querySelectorAll('.sport-widget, .market-widget').forEach(el => el.remove());

  const sport  = makeSportWidget();
  if (sport)  dayView.appendChild(sport);

  const market = digest?.market ? makeMarketWidget(digest.market) : null;
  if (market) dayView.appendChild(market);
}

// ── Market widget ──────────────────────────────────────────────────────────
function makeMarketWidget(snapshot) {
  if (!snapshot || !Object.keys(snapshot).length) return null;
  const LABELS = {
    EURUSD:'EUR/USD', EURCZK:'EUR/CZK', SP500:'S&P 500',
    DAX:'DAX', PX:'PX', BTCUSD:'BTC',
  };
  let anyAlert = false;
  const cells = Object.entries(snapshot).map(([k, v]) => {
    const pct   = typeof v.pct === 'number' ? v.pct : 0;
    const sign  = v.delta >= 0 ? '+' : '';
    const alert = pct <= MARKET_DROP_ALERT;
    if (alert) anyAlert = true;
    return `<div class="market-cell${alert ? ' alert' : ''}">
      <div class="market-name">${LABELS[k]||k}</div>
      <div class="market-value">${fmtMarketNum(v.value, k)}</div>
      <div class="market-delta ${v.delta >= 0 ? 'up' : 'down'}">${alert?'! ':''}${sign}${pct.toFixed(2)}%</div>
    </div>`;
  }).join('');

  const div = document.createElement('div');
  div.className = 'market-widget';
  div.innerHTML = `
    <div class="market-widget-title">
      Market Snapshot${anyAlert ? ' <span class="market-alert-flag">! sharp drop</span>' : ''}
    </div>
    <div class="market-grid">${cells}</div>`;
  return div;
}

function fmtMarketNum(val, ticker) {
  if (!val && val !== 0) return '—';
  if (['EURUSD','EURCZK'].includes(ticker)) return val.toFixed(4);
  if (ticker === 'BTCUSD') return val >= 1000 ? (val/1000).toFixed(1)+'k' : val.toFixed(0);
  return val >= 1000 ? (val/1000).toFixed(1)+'k' : val.toFixed(2);
}

// ── Sport widget ───────────────────────────────────────────────────────────
const FB_LEAGUE_NAMES = {
  PL:'🏴 Premier League', BL1:'🇩🇪 Bundesliga', SA:'🇮🇹 Serie A',
  PD:'🇪🇸 La Liga', FL1:'🇫🇷 Ligue 1', CL:'🏆 Champions League', MLS:'🇺🇸 MLS',
};

function fmtDay(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString(undefined, { month:'short', day:'numeric' });
}
function fmtTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d)) return '';
  return d.toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' });
}
function resultRow(home, hs, away, as_, date) {
  return `<div class="sport-result">
    ${date ? `<span class="sport-date">${fmtDay(date)}</span>` : ''}
    <span class="sport-team">${escHtml(home)}</span>
    <span class="sport-score">${hs}–${as_}</span>
    <span class="sport-team right">${escHtml(away)}</span>
  </div>`;
}
function fixtureRow(home, away, date, time, live) {
  const when = live ? 'LIVE' : (fmtTime(time) || 'TBD');
  return `<div class="sport-result fixture${live ? ' live' : ''}">
    ${date ? `<span class="sport-date">${fmtDay(date)}</span>` : ''}
    <span class="sport-team">${escHtml(home)}</span>
    <span class="sport-score">${when}</span>
    <span class="sport-team right">${escHtml(away)}</span>
  </div>`;
}

function makeSportWidget() {
  // New structure: digest.sport = { nhl: {...}, football: {...} }
  const sb = digest?.sport;
  if (!sb) return null;
  const leagues = [];

  // NHL
  if (sb.nhl) {
    let html = '';
    (sb.nhl.results||[]).forEach(r => html += resultRow(r.away, r.away_score, r.home, r.home_score, r.date));
    (sb.nhl.today ||[]).forEach(f => html += fixtureRow(f.away, f.home, f.date, f.time, false));
    if (html) leagues.push({ name:'🏒 NHL', html });
  }

  // Football
  const fb = sb.football;
  if (fb && Array.isArray(fb.sections)) {
    fb.sections.forEach(sec => {
      let html = '';
      (sec.results  ||[]).forEach(r => html += resultRow(r.home, r.home_score, r.away, r.away_score, r.date));
      (sec.fixtures ||[]).forEach(f => html += fixtureRow(f.home, f.away, f.date, f.time, f.live));
      if (!html) return;
      const name = fb.mode === 'tournament'
        ? `⚽ ${sec.name}`
        : (FB_LEAGUE_NAMES[sec.code] || sec.name || sec.code);
      leagues.push({ name, html });
    });
  } else if (fb && typeof fb === 'object') {
    // Backward compat with old flat shape
    Object.entries(fb).forEach(([code, data]) => {
      if (!data?.results?.length) return;
      let html = '';
      data.results.slice(0,5).forEach(r => html += resultRow(r.home, r.home_score, r.away, r.away_score, r.date));
      if (html) leagues.push({ name: FB_LEAGUE_NAMES[code]||code, html });
    });
  }

  if (!leagues.length) return null;

  const widget = document.createElement('div');
  widget.className = 'sport-widget';
  const banner = fb?.mode === 'tournament' && fb.competition
    ? `<div class="sport-banner">🏆 ${escHtml(fb.competition)}</div>` : '';

  widget.innerHTML = banner + leagues.map((l, i) => `
    <div class="sport-league">
      <div class="sport-league-header"
           onclick="this.nextElementSibling.classList.toggle('open');
                    this.querySelector('.sport-league-toggle').textContent=
                      this.nextElementSibling.classList.contains('open')?'▴':'▾'">
        <span class="sport-league-name">${l.name}</span>
        <span class="sport-league-toggle">${i===0?'▴':'▾'}</span>
      </div>
      <div class="sport-league-body${i===0?' open':''}">
        ${l.html}
      </div>
    </div>`).join('');

  return widget;
}

// ── Main renderer ──────────────────────────────────────────────────────────
function renderArticles() {
  if (!digest) return;

  // Header
  const dateStr = digest.date || digest.generated_at || '';
  const d = new Date(dateStr);
  const opts = { weekday:'long', day:'numeric', month:'long' };
  document.getElementById('header-date').textContent =
    isNaN(d) ? dateStr : d.toLocaleDateString(undefined, opts);

  const totalStories = Object.values(digest.categories || {})
    .reduce((sum, cat) => sum + (cat.stories?.length || 0), 0);
  const mins = digest.estimated_read_minutes || Math.ceil(totalStories * 1.5);
  document.getElementById('header-meta').textContent =
    `~${mins} min · ${totalStories} stories`;
  document.getElementById('last-updated').textContent = isNaN(d) ? dateStr : d.toLocaleString();

  buildFilters();
  renderCurrentView();
  Analytics.logDigestOpen();
}

// ── Analytics panel ────────────────────────────────────────────────────────
function renderAnalytics() {
  const m = Analytics.compute();
  document.getElementById('streak-num').textContent   = m.streak;
  document.getElementById('streak-sub').textContent   = m.streak === 0
    ? 'Open the digest daily to build your streak'
    : `${m.streak} day${m.streak!==1?'s':''} in a row — keep going!`;
  document.getElementById('stat-opens-today').textContent = m.opensToday;
  document.getElementById('stat-avg').textContent         = m.avgPerDay;
  document.getElementById('stat-fav-source').textContent  =
    m.favSource.length > 14 ? m.favSource.slice(0,13)+'…' : m.favSource;
  // learning streak no longer tracked — hide or zero that element if it exists
  const learnEl = document.getElementById('stat-learning-streak');
  if (learnEl) learnEl.textContent = '—';

  const barsEl = document.getElementById('cat-bars');
  barsEl.innerHTML = '';
  const maxCount = Math.max(1, ...Object.values(m.catCount));
  CAT_ORDER.forEach(cat => {
    const count = m.catCount[cat] || 0;
    const pct   = (count / maxCount * 100).toFixed(1);
    const meta  = CAT_META[cat] || {};
    barsEl.innerHTML += `
      <div class="cat-bar-row">
        <div class="cat-bar-emoji">${meta.emoji||''}</div>
        <div class="cat-bar-label truncate">${meta.label||cat}</div>
        <div class="cat-bar-track">
          <div class="cat-bar-fill" style="width:${pct}%;background:${meta.color||'#888'}"></div>
        </div>
        <div class="cat-bar-count">${count}</div>
      </div>`;
  });

  const raw = localStorage.getItem(ANALYTICS_KEY) || '[]';
  const kb  = (new Blob([raw]).size / 1024).toFixed(1);
  document.getElementById('analytics-size').textContent = `${kb} KB stored locally`;
}

// ── Settings ───────────────────────────────────────────────────────────────
function initSettings() {
  document.getElementById('clear-analytics-btn')?.addEventListener('click', () => {
    if (!confirm('Clear all analytics data? This cannot be undone.')) return;
    localStorage.removeItem(ANALYTICS_KEY);
    renderAnalytics();
    showToast('Analytics cleared');
  });
}

// ── Pull-to-refresh ────────────────────────────────────────────────────────
function initPullToRefresh() {
  let startY = 0, pulling = false;
  const main = document.getElementById('main');
  main.addEventListener('touchstart', e => {
    if (main.scrollTop === 0) { startY = e.touches[0].clientY; pulling = true; }
  }, { passive: true });
  main.addEventListener('touchmove', e => {
    if (!pulling) return;
    if (e.touches[0].clientY - startY > 60)
      document.getElementById('ptr-indicator')?.classList.add('visible');
  }, { passive: true });
  main.addEventListener('touchend', async () => {
    if (!pulling) return;
    pulling = false;
    document.getElementById('ptr-indicator')?.classList.remove('visible');
    await refreshDigest();
  });
}

async function refreshDigest() {
  showLoading(true);
  try {
    digest = await loadDigest(currentDate);
    renderArticles();
    showToast('Digest refreshed');
  } catch { showToast('Could not refresh'); }
  finally  { showLoading(false); }
}

// ── Navigation ─────────────────────────────────────────────────────────────
function initNav() {
  document.querySelectorAll('.nav-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const panel = document.getElementById(btn.dataset.panel + '-panel');
      if (panel) panel.classList.add('active');
      if (btn.dataset.panel === 'analytics') renderAnalytics();
    });
  });

  document.querySelectorAll('.view-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentView = btn.dataset.view;
      renderCurrentView();
    });
  });

  document.getElementById('refresh-btn')?.addEventListener('click', refreshDigest);
}

// ── Utilities ──────────────────────────────────────────────────────────────
function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function showLoading(on) {
  document.getElementById('loading').classList.toggle('hidden', !on);
  document.getElementById('app').style.display = on ? 'none' : '';
}

let toastTimer;
function showToast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 2200);
}

function registerSW() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
}

// ── Startup ────────────────────────────────────────────────────────────────
async function init() {
  registerSW();
  initNav();
  initSettings();
  initPullToRefresh();

  const today = new Date().toISOString().slice(0, 10);
  currentDate = today;
  buildCalendar();

  try {
    digest = await loadDigest();
    if (digest.date) currentDate = digest.date;
    buildCalendar();
    renderArticles();
  } catch {
    document.getElementById('loading').innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📭</div>
        <p>No digest available yet</p>
        <small>The pipeline runs daily at 05:30 UTC</small>
      </div>`;
    return;
  }

  showLoading(false);
}

document.addEventListener('DOMContentLoaded', init);
