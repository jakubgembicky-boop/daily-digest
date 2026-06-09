/* Daily Digest PWA — app.js
   Vanilla JS only. No frameworks, no CDN, no external fonts.
   localStorage usage: ONLY for analytics events (key: digest_analytics).
*/

'use strict';

// ── Constants ──────────────────────────────────────────────────────────────
const ANALYTICS_KEY = 'digest_analytics';
const DIGEST_LATEST = 'digest.json';
const DIGEST_ARCHIVE = date => `digests/${date}.json`;

const CAT_COLORS = {
  slovakia:'#0080C7', czechia:'#B45309',  europe:'#003399', war:'#CC2222',
  sport:   '#1DB954', global: '#F59E0B',  tech:  '#7C3AED', economy:'#6B7280',
  hr:      '#0891B2', health: '#059669',  random:'#EC4899', learning:'#6366F1',
};
const CAT_EMOJIS = {
  slovakia:'🇸🇰', czechia:'🇨🇿', europe:'🇪🇺', war:'🔴',
  sport:   '🏒',  global: '🌍',  tech:  '💻',  economy:'📈',
  hr:      '👥',  health: '🏃',  random:'🎲',  learning:'📚',
};
const CAT_ORDER = [
  'slovakia','czechia','europe','war','sport','global',
  'tech','economy','hr','health','random','learning'
];

// ── State ──────────────────────────────────────────────────────────────────
let digest       = null;   // loaded digest.json
let currentDate  = null;   // YYYY-MM-DD of displayed digest
let currentView  = 'day';  // 'day' | 'week' | 'month'
let activeFilters = new Set(); // empty = all categories shown
let readSet      = new Set(); // article ids marked read this session

// ── Analytics helpers ──────────────────────────────────────────────────────
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
    // Keep last 180 days max
    const cutoff = Date.now() - 180 * 86400_000;
    this.save(events.filter(e => e.ts > cutoff));
  },

  // ── Event logging ────────────────────────────────────────────────────────
  logDigestOpen() {
    this.push({ type: 'digest_open' });
  },
  logArticleOpen(story, source) {
    this.push({
      type: 'article_open',
      article_id:  story.id,
      category:    story.category,
      source:      source.source,
      is_subscription: source.is_subscription,
    });
  },
  logSpecialOpen(kind) {
    this.push({ type: 'special_open', kind });
  },
  logFeedback(articleId, category, vote) {
    this.push({ type: 'feedback', article_id: articleId, category, vote });
  },

  // ── Computed metrics ─────────────────────────────────────────────────────
  compute() {
    const events = this.load();
    const now    = Date.now();
    const d7     = now - 7 * 86400_000;
    const d30    = now - 30 * 86400_000;
    const d24    = now - 86400_000;

    // Reading streak: consecutive days with digest_open
    const openDays = new Set(
      events.filter(e => e.type === 'digest_open')
            .map(e => new Date(e.ts).toDateString())
    );
    let streak = 0;
    const today = new Date();
    for (let i = 0; i < 365; i++) {
      const d = new Date(today); d.setDate(d.getDate() - i);
      if (openDays.has(d.toDateString())) streak++;
      else break;
    }

    // Learning streak
    const learnDays = new Set(
      events.filter(e => e.type === 'special_open' && e.kind === 'learning')
            .map(e => new Date(e.ts).toDateString())
    );
    let learnStreak = 0;
    for (let i = 0; i < 365; i++) {
      const d = new Date(today); d.setDate(d.getDate() - i);
      if (learnDays.has(d.toDateString())) learnStreak++;
      else break;
    }

    // Today's opens
    const opensToday = events.filter(e => e.type === 'article_open' && e.ts > d24).length;

    // Avg per day (last 30)
    const openDays30 = new Set(
      events.filter(e => e.type === 'article_open' && e.ts > d30)
            .map(e => new Date(e.ts).toDateString())
    );
    const totalOpens30 = events.filter(e => e.type === 'article_open' && e.ts > d30).length;
    const avgPerDay = openDays30.size > 0 ? (totalOpens30 / 30).toFixed(1) : '0';

    // Favourite source (last 30)
    const srcCount = {};
    events.filter(e => e.type === 'article_open' && e.ts > d30)
          .forEach(e => { srcCount[e.source] = (srcCount[e.source] || 0) + 1; });
    const favSource = Object.entries(srcCount).sort((a,b) => b[1]-a[1])[0]?.[0] || '—';

    // Category breakdown (this month)
    const monthStart = new Date();
    monthStart.setDate(1); monthStart.setHours(0,0,0,0);
    const catCount = {};
    events.filter(e => e.type === 'article_open' && e.ts > monthStart.getTime())
          .forEach(e => { catCount[e.category] = (catCount[e.category] || 0) + 1; });

    return { streak, learnStreak, opensToday, avgPerDay, favSource, catCount };
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
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const iso = d.toISOString().slice(0, 10);
    const dayNames = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];

    const btn = document.createElement('button');
    btn.className = 'cal-day' + (i === 0 ? ' today' : '');
    if (iso === currentDate) btn.classList.add('selected');
    btn.dataset.date = iso;
    btn.innerHTML = `<span class="day-name">${dayNames[d.getDay()]}</span>
                     <span class="day-num">${d.getDate()}</span>`;
    btn.addEventListener('click', () => switchDate(iso));
    strip.appendChild(btn);
  }
  // Scroll to end (today)
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
  } catch {
    showToast('No digest for ' + date);
  } finally {
    showLoading(false);
  }
}

// ── Category filters ───────────────────────────────────────────────────────
function buildFilters() {
  const ctrl = document.getElementById('view-controls');
  // Remove old filter buttons
  ctrl.querySelectorAll('.cat-filter,.filter-sep').forEach(el => {
    if (!el.dataset.view) el.remove();
  });

  if (!digest) return;
  const sep = document.createElement('div');
  sep.className = 'filter-sep';
  ctrl.appendChild(sep);

  const cats = CAT_ORDER.filter(c => digest.categories[c]);
  cats.forEach(cat => {
    const btn = document.createElement('button');
    btn.className = 'cat-filter' + (activeFilters.has(cat) ? ' active' : '');
    btn.dataset.cat = cat;
    btn.style.setProperty('--cat-active', CAT_COLORS[cat] || '#888');
    if (activeFilters.has(cat)) btn.style.background = CAT_COLORS[cat];
    btn.innerHTML = `<span class="filter-dot" style="background:${CAT_COLORS[cat]||'#888'}"></span>
                     ${CAT_EMOJIS[cat]||''} ${digest.categories[cat].label}`;
    btn.addEventListener('click', () => toggleFilter(cat));
    ctrl.appendChild(btn);
  });
}

function toggleFilter(cat) {
  if (activeFilters.has(cat)) activeFilters.delete(cat);
  else activeFilters.add(cat);
  buildFilters();
  renderCurrentView();
}

function visibleStories() {
  if (!digest) return [];
  const all = [];
  CAT_ORDER.forEach(cat => {
    const block = digest.categories[cat];
    if (!block) return;
    if (activeFilters.size > 0 && !activeFilters.has(cat)) return;
    block.stories.forEach(s => all.push({ ...s, category: cat }));
  });
  return all;
}

// ── Card rendering ─────────────────────────────────────────────────────────
function makeCard(story) {
  const cat      = story.category;
  const color    = CAT_COLORS[cat] || '#888';
  const isRandom   = cat === 'random';
  const isLearning = cat === 'learning';
  const isRead   = readSet.has(story.id);

  const card = document.createElement('div');
  card.className = 'story-card' +
    (isRandom   ? ' card-random'   : '') +
    (isLearning ? ' card-learning' : '') +
    (isRead     ? ' read'          : '');
  card.style.setProperty('--cat-color', color);
  card.dataset.id = story.id;

  // Special header bars
  let specialHeader = '';
  if (isRandom)   specialHeader = `<div class="card-random-header">🎲 Today's Surprise</div>`;
  if (isLearning) specialHeader = `<div class="card-learning-header">📚 Learn Something</div>`;

  // Image / placeholder
  const imgSrc = story.sources?.[0]?.image_url;
  const imgEl = imgSrc
    ? `<img class="card-img" src="${escHtml(imgSrc)}" alt="" loading="lazy" onerror="this.parentNode.replaceChild(Object.assign(document.createElement('div'),{className:'card-img-placeholder',textContent:'${CAT_EMOJIS[cat]||'📰'}'}),this)">`
    : `<div class="card-img-placeholder">${CAT_EMOJIS[cat] || '📰'}</div>`;

  // Badges
  let badges = '';
  if (story.is_top5)    badges += `<span class="badge badge-top5">⭐ Top Story</span>`;
  if (story.is_breaking)badges += `<span class="badge badge-breaking">🔴 Breaking</span>`;
  const srcCount = story.sources?.length || 0;
  if (srcCount > 1) badges += `<span class="badge badge-sources">${srcCount} sources</span>`;

  // Domain pill for learning
  const domainPill = isLearning && story.domain
    ? `<span class="card-domain-pill">${story.domain}</span>` : '';

  // Hook line
  const hookLine = (isRandom || isLearning) && story.hook
    ? `<div class="card-hook">${escHtml(story.hook)}</div>` : '';

  card.innerHTML = `
    ${specialHeader}
    ${imgEl}
    <div class="card-body">
      <div class="card-cat-row">
        <div class="card-cat-dot"></div>
        <div class="card-cat-label">${escHtml(digest.categories[cat]?.label || cat)}</div>
        ${domainPill}
      </div>
      <div class="card-title">${escHtml(story.topic)}</div>
      ${hookLine}
      ${badges ? `<div class="card-badges">${badges}</div>` : ''}
    </div>
    <div class="card-actions">
      <button class="card-open-btn" data-action="expand">
        ${srcCount} source${srcCount !== 1 ? 's' : ''} ▾
      </button>
      <div class="card-like-row">
        <button class="like-btn" data-action="like" title="Like">👍</button>
        <button class="dislike-btn" data-action="dislike" title="Dislike">👎</button>
      </div>
    </div>
    <div class="card-sources-list" id="sources-${story.id}">
      ${(story.sources || []).map(src => `
        <div class="source-row">
          <div class="source-info">
            <div class="source-name">
              ${escHtml(src.source)}
              ${src.is_subscription ? '<span class="sub-icon" title="Subscription">💎</span>' : ''}
              <span class="source-angle">${escHtml(src.angle || 'news')}</span>
            </div>
            <div class="source-summary">${escHtml(src.summary || '')}</div>
          </div>
          ${src.url ? `<a class="source-open" href="${escHtml(src.url)}" target="_blank" rel="noopener"
              data-source="${escHtml(src.source)}" data-story-id="${story.id}">
              Open ↗
            </a>` : ''}
        </div>
      `).join('')}
    </div>`;

  // Events
  card.addEventListener('click', e => {
    const action = e.target.closest('[data-action]')?.dataset.action;
    if (action === 'expand') {
      const list = card.querySelector('.card-sources-list');
      const btn  = card.querySelector('.card-open-btn');
      const open = list.classList.toggle('open');
      btn.textContent = open ? 'Close ▴' : `${srcCount} source${srcCount !== 1 ? 's' : ''} ▾`;
      if (!isRead) {
        readSet.add(story.id);
        card.classList.add('read');
        sinkReadCards();
      }
      if (isRandom)   Analytics.logSpecialOpen('random');
      if (isLearning) Analytics.logSpecialOpen('learning');
      return;
    }
    if (action === 'like' || action === 'dislike') {
      const btn = e.target.closest('[data-action]');
      btn.classList.toggle('voted');
      Analytics.logFeedback(story.id, cat, action);
      showToast(action === 'like' ? 'More like this 👍' : 'Less like this 👎');
      return;
    }
    // Open link tap on source-open anchor
    const anchor = e.target.closest('a.source-open');
    if (anchor) {
      const src = story.sources?.find(s => s.source === anchor.dataset.source);
      if (src) Analytics.logArticleOpen(story, src);
      if (!isRead) { readSet.add(story.id); card.classList.add('read'); sinkReadCards(); }
      return;
    }
  });

  return card;
}

function sinkReadCards() {
  const grid = document.getElementById('cards-grid');
  const cards = [...grid.querySelectorAll('.story-card')];
  const unread = cards.filter(c => !c.classList.contains('read'));
  const read   = cards.filter(c =>  c.classList.contains('read'));
  unread.forEach(c => grid.appendChild(c));
  read.forEach(c  => grid.appendChild(c));
}

// ── Day view ───────────────────────────────────────────────────────────────
function renderDayView() {
  const grid = document.getElementById('cards-grid');
  grid.innerHTML = '';
  document.getElementById('day-view').style.display   = '';
  document.getElementById('week-month-view').style.display = 'none';

  // Inject market widget in economy if economy stories exist
  const econBlock = digest?.categories?.economy;
  if (econBlock?.market_snapshot) {
    const widget = makeMarketWidget(econBlock.market_snapshot);
    if (widget) grid.parentElement.insertBefore(widget, grid);
  }

  const stories = visibleStories();
  if (!stories.length) {
    grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">
      <div class="empty-icon">📭</div>
      <p>No stories match the current filter</p>
    </div>`;
    return;
  }

  // Shuffle within day (per spec), keeping top5 with badge but randomly placed
  const shuffled = [...stories].sort(() => Math.random() - 0.5);
  shuffled.forEach(story => grid.appendChild(makeCard(story)));
  sinkReadCards();
}

// ── Week / Month view ──────────────────────────────────────────────────────
function renderGroupedView() {
  const container = document.getElementById('week-month-view');
  container.innerHTML = '';
  document.getElementById('day-view').style.display        = 'none';
  document.getElementById('week-month-view').style.display = '';

  if (!digest) return;
  const cats = CAT_ORDER.filter(c => {
    if (activeFilters.size > 0 && !activeFilters.has(c)) return false;
    return digest.categories[c]?.stories?.length > 0;
  });

  cats.forEach(cat => {
    const block    = digest.categories[cat];
    const color    = CAT_COLORS[cat] || '#888';
    const section  = document.createElement('div');
    section.className = 'cat-section';
    section.innerHTML = `
      <div class="cat-section-header">
        <div class="cat-section-dot" style="background:${color}"></div>
        <div class="cat-section-title">${CAT_EMOJIS[cat]||''} ${block.label}</div>
        <div class="cat-section-count">${block.stories.length} stories</div>
      </div>
      <div class="cat-section-grid"></div>`;
    const grid = section.querySelector('.cat-section-grid');
    block.stories.forEach(s => grid.appendChild(makeCard({ ...s, category: cat })));
    container.appendChild(section);
  });
}

function renderCurrentView() {
  if (currentView === 'day') renderDayView();
  else renderGroupedView();
}

// ── Market widget ──────────────────────────────────────────────────────────
function makeMarketWidget(snapshot) {
  if (!snapshot || !Object.keys(snapshot).length) return null;
  const LABELS = {
    EURUSD:'EUR/USD', EURCZK:'EUR/CZK', SP500:'S&P 500',
    DAX:'DAX', PX:'PX', BTCUSD:'BTC',
  };
  const div = document.createElement('div');
  div.className = 'market-widget';
  const cells = Object.entries(snapshot).map(([k, v]) => {
    const sign  = v.delta >= 0 ? '+' : '';
    const cls   = v.delta >= 0 ? 'up' : 'down';
    return `<div class="market-cell">
      <div class="market-name">${LABELS[k] || k}</div>
      <div class="market-value">${formatNum(v.value, k)}</div>
      <div class="market-delta ${cls}">${sign}${v.pct?.toFixed(2)}%</div>
    </div>`;
  }).join('');
  div.innerHTML = `<div class="market-widget-title">Market Snapshot</div>
                   <div class="market-grid">${cells}</div>`;
  return div;
}

function formatNum(val, ticker) {
  if (!val) return '—';
  if (['EURUSD','EURCZK'].includes(ticker)) return val.toFixed(4);
  if (ticker === 'BTCUSD') return val >= 1000 ? (val/1000).toFixed(1)+'k' : val.toFixed(0);
  return val >= 1000 ? (val/1000).toFixed(1)+'k' : val.toFixed(2);
}

// ── Sport widget ───────────────────────────────────────────────────────────
function injectSportWidget() {
  const sportBlock = digest?.categories?.sport;
  if (!sportBlock?.scoreboard) return;
  const grid = document.getElementById('cards-grid');

  const widget = document.createElement('div');
  widget.className = 'sport-widget';
  widget.style.gridColumn = '1 / -1';

  const sb = sportBlock.scoreboard;
  const leagues = [];

  if (sb.nhl) {
    const results = sb.nhl.results || [];
    const today   = sb.nhl.today   || [];
    let html = '';
    results.forEach(r => {
      html += `<div class="sport-result">
        <span class="sport-team">${r.away}</span>
        <span class="sport-score">${r.away_score}–${r.home_score}</span>
        <span class="sport-team" style="text-align:right">${r.home}</span>
      </div>`;
    });
    today.forEach(f => {
      const t = f.time ? new Date(f.time).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) : '';
      html += `<div class="sport-result" style="opacity:.6">
        <span class="sport-team">${f.away}</span>
        <span class="sport-score" style="font-size:11px">${t||'TBD'}</span>
        <span class="sport-team" style="text-align:right">${f.home}</span>
      </div>`;
    });
    if (!html) html = '<div class="sport-empty">No games today</div>';
    leagues.push({ name: '🏒 NHL', html });
  }

  if (sb.football) {
    const LEAGUE_NAMES = { PL:'🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League', BL1:'🇩🇪 Bundesliga',
      SA:'🇮🇹 Serie A', PD:'🇪🇸 La Liga', FL1:'🇫🇷 Ligue 1',
      CL:'🏆 Champions League', MLS:'🇺🇸 MLS' };
    Object.entries(sb.football).forEach(([code, data]) => {
      const results = (data.results || []).slice(0, 5);
      let html = '';
      results.forEach(r => {
        html += `<div class="sport-result">
          <span class="sport-team">${r.home}</span>
          <span class="sport-score">${r.home_score}–${r.away_score}</span>
          <span class="sport-team" style="text-align:right">${r.away}</span>
        </div>`;
      });
      if (!html) html = '<div class="sport-empty">No recent results</div>';
      leagues.push({ name: LEAGUE_NAMES[code] || code, html });
    });
  }

  widget.innerHTML = leagues.map((l, i) => `
    <div class="sport-league">
      <div class="sport-league-header" onclick="this.nextElementSibling.classList.toggle('open');this.querySelector('.sport-league-toggle').textContent=this.nextElementSibling.classList.contains('open')?'▴':'▾'">
        <span class="sport-league-name">${l.name}</span>
        <span class="sport-league-toggle">${i===0?'▴':'▾'}</span>
      </div>
      <div class="sport-league-body${i===0?' open':''}">
        ${l.html}
      </div>
    </div>`).join('');

  grid.insertBefore(widget, grid.firstChild);
}

// ── Main article renderer ──────────────────────────────────────────────────
function renderArticles() {
  if (!digest) return;

  // Header
  const genAt = new Date(digest.generated_at);
  const opts = { weekday:'long', day:'numeric', month:'long' };
  document.getElementById('header-date').textContent =
    genAt.toLocaleDateString(undefined, opts);
  document.getElementById('header-meta').textContent =
    `~${digest.estimated_read_minutes} min · ${digest.total_stories} stories · ` +
    genAt.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  document.getElementById('last-updated').textContent =
    genAt.toLocaleString();

  buildFilters();
  renderCurrentView();

  // Inject widgets into day view after grid is built
  if (currentView === 'day') {
    injectSportWidget();
  }

  Analytics.logDigestOpen();
}

// ── Analytics panel renderer ───────────────────────────────────────────────
function renderAnalytics() {
  const m = Analytics.compute();
  document.getElementById('streak-num').textContent        = m.streak;
  document.getElementById('streak-sub').textContent        = m.streak === 0
    ? 'Open the digest daily to build your streak'
    : `${m.streak} day${m.streak!==1?'s':''} in a row — keep going!`;
  document.getElementById('stat-opens-today').textContent  = m.opensToday;
  document.getElementById('stat-avg').textContent          = m.avgPerDay;
  document.getElementById('stat-fav-source').textContent   = m.favSource.length > 12
    ? m.favSource.slice(0,11)+'…' : m.favSource;
  document.getElementById('stat-learning-streak').textContent = m.learnStreak;

  const barsEl = document.getElementById('cat-bars');
  barsEl.innerHTML = '';
  const maxCount = Math.max(1, ...Object.values(m.catCount));
  CAT_ORDER.forEach(cat => {
    const count = m.catCount[cat] || 0;
    const pct   = (count / maxCount * 100).toFixed(1);
    const color = CAT_COLORS[cat] || '#888';
    const emoji = CAT_EMOJIS[cat] || '';
    const catMeta = digest?.categories?.[cat];
    barsEl.innerHTML += `
      <div class="cat-bar-row">
        <div class="cat-bar-emoji">${emoji}</div>
        <div class="cat-bar-label truncate">${catMeta?.label || cat}</div>
        <div class="cat-bar-track">
          <div class="cat-bar-fill" style="width:${pct}%;background:${color}"></div>
        </div>
        <div class="cat-bar-count">${count}</div>
      </div>`;
  });

  // Analytics data size
  const raw = localStorage.getItem(ANALYTICS_KEY) || '[]';
  const kb  = (new Blob([raw]).size / 1024).toFixed(1);
  document.getElementById('analytics-size').textContent = `${kb} KB stored locally`;
}

// ── Settings ───────────────────────────────────────────────────────────────
function initSettings() {
  document.getElementById('clear-analytics-btn').addEventListener('click', () => {
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
    const delta = e.touches[0].clientY - startY;
    if (delta > 60) {
      document.getElementById('ptr-indicator')?.classList.add('visible');
    }
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
  } catch (err) {
    showToast('Could not refresh');
  } finally {
    showLoading(false);
  }
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
      if (currentView === 'day') injectSportWidget();
    });
  });

  document.getElementById('refresh-btn').addEventListener('click', refreshDigest);
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

// ── Service Worker ─────────────────────────────────────────────────────────
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
  } catch (err) {
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
