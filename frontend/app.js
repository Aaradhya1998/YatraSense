const BASE_URL = 'http://localhost:8000';

async function readJson(res) {
  if (!res.ok) throw new Error(`Request failed with ${res.status}`);
  return res.json();
}

async function fetchCrowdStatus(video = 'low_crowd') {
  const res = await fetch(`${BASE_URL}/crowd-status?video=${video}`);
  return readJson(res);
}

async function fetchMonumentInfo() {
  const res = await fetch(`${BASE_URL}/monument-info`);
  return readJson(res);
}

async function fetchHistoricalPattern() {
  const res = await fetch(`${BASE_URL}/historical-pattern`);
  return readJson(res);
}

async function fetchAlerts() {
  const res = await fetch(`${BASE_URL}/alerts`);
  return readJson(res);
}

async function postSOS(message = 'Tourist SOS triggered') {
  const res = await fetch(`${BASE_URL}/sos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  });
  return res.json();
}

async function postSimulate(video) {
  const res = await fetch(`${BASE_URL}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ video })
  });
  return res.json();
}

function getDensityClass(level) {
  return typeof level === 'string' ? level.toLowerCase() : 'low';
}

function getDensityLabel(level) {
  const map = { LOW: 'Low Crowd', MEDIUM: 'Moderate', HIGH: 'High Crowd' };
  const key = typeof level === 'string' ? level.toUpperCase() : '';
  return map[key] || 'Low Crowd';
}

function showToast(message, isError = false) {
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = message;
  if (isError) t.style.background = 'var(--density-high)';
  document.body.appendChild(t);
  requestAnimationFrame(() => t.classList.add('show'));
  setTimeout(() => {
    t.classList.remove('show');
    setTimeout(() => t.remove(), 300);
  }, 2800);
}

function showAuthorityCallButton() {
  const existing = document.querySelector('[data-authority-call-button]');
  if (existing) existing.remove();

  const callBtn = document.createElement('div');
  callBtn.dataset.authorityCallButton = 'true';
  callBtn.style.cssText = `
    position: fixed;
    bottom: 140px;
    left: 50%;
    transform: translateX(-50%);
    background: var(--density-high);
    color: white;
    font-family: 'Nunito', sans-serif;
    font-weight: 700;
    font-size: 16px;
    padding: 14px 32px;
    border-radius: 24px;
    cursor: pointer;
    z-index: 1001;
    box-shadow: 0 4px 20px rgba(192,57,43,0.5);
    white-space: nowrap;
  `;
  callBtn.textContent = 'Call Authority Now';
  callBtn.onclick = () => window.open('tel:+911800110');
  document.body.appendChild(callBtn);
  setTimeout(() => callBtn.remove(), 8000);
}

function safeText(value, fallback = 'Unavailable') {
  if (value === null || value === undefined || value === '') return fallback;
  if (typeof value === 'object') return fallback;
  return String(value);
}

function setDensityBadges(level) {
  const density = getDensityClass(normalizeDensity(level));
  const label = density.toUpperCase();

  document.querySelectorAll('[data-density-badge]').forEach(badge => {
    badge.classList.remove('skeleton-badge', 'low', 'medium', 'high');
    badge.classList.add(density);
    badge.textContent = label;
  });
}

function setRecommendation(text) {
  document.querySelectorAll('[data-ai-recommendation]').forEach(panel => {
    panel.textContent = safeText(text, 'Live data unavailable');
  });
}

function setInfoValue(field, value) {
  const element = document.querySelector(`[data-info-field="${field}"]`);
  if (element) element.textContent = safeText(value);
}

function formatHours(hours) {
  if (!hours || typeof hours !== 'object') return null;
  return hours.open && hours.close ? `${hours.open}-${hours.close}` : null;
}

function formatTicket(ticket) {
  if (!ticket || typeof ticket !== 'object') return null;
  const currency = safeText(ticket.currency, 'INR');
  return ticket.indian ? `${currency} ${ticket.indian}` : null;
}

function convertTo12h(time24) {
  if (typeof time24 !== 'string') return null;
  const match = time24.match(/^(\d{1,2}):(\d{2})/);
  if (!match) return null;

  const hour24 = Number(match[1]);
  const minute = match[2];
  const suffix = hour24 >= 12 ? 'PM' : 'AM';
  const hour12 = hour24 % 12 || 12;
  return `${hour12}:${minute} ${suffix}`;
}

function normalizeDensity(level) {
  const value = typeof level === 'string' ? level.toUpperCase() : 'LOW';
  if (value === 'LOW' || value === 'MEDIUM' || value === 'HIGH') return value;
  return 'LOW';
}

function getMonumentTickets(monument) {
  return monument.tickets || monument.ticket_price || {};
}

function getMonumentParking(monument) {
  const parking = monument.parking || {};
  if (typeof parking === 'object' && parking !== null) return parking.cost;
  return monument.parking_price || parking;
}

function getSmartHeadline(crowd) {
  const density = normalizeDensity(crowd.current_density);
  const eta = crowd.forecast && crowd.forecast.eta_minutes;

  if (density === 'LOW') return 'Great time to visit. Crowd is LOW right now.';
  if (density === 'MEDIUM') return `Visit soon - crowd dropping in ~${safeText(eta, '15')} min.`;
  return `Busy right now. Best to wait ~${safeText(eta, '30')} min.`;
}

function updateSmartPanel(crowd) {
  const headline = document.querySelector('[data-smart-headline]');
  const subline = document.querySelector('[data-smart-subline]');
  if (!headline || !subline) return;

  const forecast = crowd.forecast || {};
  headline.textContent = getSmartHeadline(crowd);
  subline.textContent = `~${safeText(crowd.person_count_estimate, '0')} people estimated inside - Forecast: ${safeText(forecast.label, 'Unavailable')}`;
}

function updateDetailMonument(monument) {
  const hours = monument.hours || {};
  const tickets = getMonumentTickets(monument);
  const parkingCost = getMonumentParking(monument);
  const open = convertTo12h(hours.open);
  const close = convertTo12h(hours.close);
  const hoursText = open && close ? `${open} - ${close}` : 'Unavailable';
  const entryText = tickets.indian && tickets.foreign ? `Rs ${tickets.indian} / Rs ${tickets.foreign}` : 'Unavailable';
  const parkingText = parkingCost ? `Rs ${parkingCost}` : 'Unavailable';

  setInfoValue('hours', hoursText);
  setInfoValue('entry', entryText);
  setInfoValue('parking', parkingText);

  const openPill = document.querySelector('[data-open-pill]');
  const hoursPill = document.querySelector('[data-hours-pill]');
  const entryPill = document.querySelector('[data-entry-pill]');
  if (openPill) openPill.textContent = close ? `Open until ${close}` : 'Hours unavailable';
  if (hoursPill) hoursPill.textContent = open && close ? `Hours: Open - ${open} to ${close}` : 'Hours: Unavailable';
  if (entryPill) entryPill.textContent = tickets.indian ? `Entry: Rs ${tickets.indian}` : 'Entry: Unavailable';
}

function populateCrowdData(crowdData) {
  setDensityBadges(crowdData.current_density);
  updateSmartPanel(crowdData);
}

function populateMonumentData(monumentData) {
  updateDetailMonument(monumentData);
}

function populatePatternData(patternData) {
  renderWeeklyGraph(patternData);
}

function populateFallbackData() {
  populateCrowdData({
    current_density: 'MEDIUM',
    person_count_estimate: 14,
    forecast: { label: 'LOW', text: 'Crowd likely to ease in ~20 minutes', eta_minutes: 20 }
  });
  populateMonumentData({
    name: 'Shaniwarwada Fort',
    hours: { open: '08:00', close: '18:30' },
    tickets: { indian: 25, foreign: 300 },
    parking: { cost: 30 }
  });
  populatePatternData({
    week: [
      { day: 'Mon', level: 'MEDIUM' },
      { day: 'Tue', level: 'MEDIUM' },
      { day: 'Wed', level: 'MEDIUM' },
      { day: 'Thu', level: 'MEDIUM' },
      { day: 'Fri', level: 'HIGH' },
      { day: 'Sat', level: 'HIGH' },
      { day: 'Sun', level: 'HIGH' }
    ]
  });

  const smartHeadline = document.querySelector('[data-smart-headline]');
  if (smartHeadline) smartHeadline.textContent = 'Backend offline - live data unavailable';
}

function renderWeeklyGraph() {
  const container = document.querySelector('[data-weekly-bars]');
  if (!container) return;

  const HOURLY_PATTERN = {
    Mon: { 9: 'LOW', 11: 'MEDIUM', 13: 'MEDIUM', 15: 'LOW', 17: 'LOW' },
    Tue: { 9: 'LOW', 11: 'MEDIUM', 13: 'MEDIUM', 15: 'LOW', 17: 'LOW' },
    Wed: { 9: 'LOW', 11: 'MEDIUM', 13: 'HIGH', 15: 'MEDIUM', 17: 'LOW' },
    Thu: { 9: 'LOW', 11: 'MEDIUM', 13: 'MEDIUM', 15: 'LOW', 17: 'LOW' },
    Fri: { 9: 'MEDIUM', 11: 'HIGH', 13: 'HIGH', 15: 'HIGH', 17: 'MEDIUM' },
    Sat: { 9: 'MEDIUM', 11: 'HIGH', 13: 'HIGH', 15: 'HIGH', 17: 'HIGH' },
    Sun: { 9: 'LOW', 11: 'HIGH', 13: 'HIGH', 15: 'HIGH', 17: 'MEDIUM' }
  };
  const hours = [9, 11, 13, 15, 17];
  const today = new Date().toLocaleDateString('en-US', { weekday: 'short' });
  const heights = { LOW: 30, MEDIUM: 55, HIGH: 80 };
  const labels = { LOW: 'Low', MEDIUM: 'Moderate', HIGH: 'High' };

  container.innerHTML = '';
  Object.entries(HOURLY_PATTERN).forEach(([day, dayPattern]) => {
    const group = document.createElement('div');
    group.className = `weekly-day-group${day === today ? ' today' : ''}`;

    const bars = document.createElement('div');
    bars.className = 'weekly-mini-bars';

    if (day === today) {
      const todayLabel = document.createElement('span');
      todayLabel.className = 'today-label';
      todayLabel.textContent = 'Today';
      group.append(todayLabel);
    }

    hours.forEach(hour => {
      const level = normalizeDensity(dayPattern[hour]);
      const barButton = document.createElement('button');
      barButton.className = 'weekly-bar-button';
      barButton.type = 'button';
      barButton.setAttribute('aria-label', `typically ${level.toLowerCase()} at ${formatGraphHour(hour)} on ${day}s`);

      const tooltip = document.createElement('span');
      tooltip.className = 'bar-tooltip-detail';
      tooltip.textContent = `typically ${level.toLowerCase()} at ${formatGraphHour(hour)} on ${day}s`;

      const bar = document.createElement('span');
      bar.className = `weekly-bar ${level.toLowerCase()}`;
      bar.style.height = '0px';
      requestAnimationFrame(() => {
        bar.style.height = `${heights[level]}px`;
      });

      barButton.append(tooltip, bar);
      barButton.addEventListener('click', () => {
        container.querySelectorAll('.weekly-bar-button').forEach(item => item.classList.remove('show-tooltip'));
        barButton.classList.add('show-tooltip');
      });
      bars.appendChild(barButton);
    });

    const label = document.createElement('span');
    label.className = 'weekly-day';
    label.textContent = day;

    group.append(bars, label);
    container.appendChild(group);
  });

  const legend = document.createElement('div');
  legend.className = 'weekly-legend';
  ['LOW', 'MEDIUM', 'HIGH'].forEach(level => {
    const item = document.createElement('span');
    item.className = 'weekly-legend-item';
    const dot = document.createElement('span');
    dot.className = `weekly-legend-dot ${level.toLowerCase()}`;
    item.append(dot, document.createTextNode(labels[level]));
    legend.appendChild(item);
  });
  container.appendChild(legend);
}

function formatGraphHour(hour) {
  if (hour === 13) return '1pm';
  if (hour === 15) return '3pm';
  if (hour === 17) return '5pm';
  return `${hour}am`;
}

function showBackendError() {
  document.querySelectorAll('[data-backend-warning]').forEach(banner => {
    banner.hidden = false;
  });

  setRecommendation('Backend offline - live data unavailable');
  const smartHeadline = document.querySelector('[data-smart-headline]');
  const smartSubline = document.querySelector('[data-smart-subline]');
  if (smartHeadline) smartHeadline.textContent = 'Backend offline - live data unavailable';
  if (smartSubline) smartSubline.textContent = 'Live crowd estimates and forecast timing cannot be loaded.';
  setInfoValue('hours', 'Unavailable');
  setInfoValue('entry', 'Unavailable');
  setInfoValue('parking', 'Unavailable');
}

function showErrorBanner() {
  showBackendError();
}

async function initLiveData() {
  const hasLiveWidgets = document.querySelector('[data-density-badge]') ||
    document.querySelector('[data-ai-recommendation]') ||
    document.querySelector('[data-info-field]');

  if (!hasLiveWidgets) return;

  try {
    const [crowd, monument] = await Promise.all([
      fetchCrowdStatus('low_crowd'),
      fetchMonumentInfo(),
      fetchHistoricalPattern()
    ]);

    setDensityBadges(crowd.current_density);
    setRecommendation(crowd.forecast && crowd.forecast.text);
    setInfoValue('hours', formatHours(monument.hours));
    setInfoValue('entry', formatTicket(monument.ticket_price));
    setInfoValue('parking', monument.parking_price ? `INR ${monument.parking_price}` : null);
  } catch (error) {
    console.error('Backend fetch failed:', error);
    showErrorBanner();
    populateFallbackData();
  }
}

async function refreshDetailCrowd() {
  const crowdData = await fetchCrowdStatus('low_crowd');
  setDensityBadges(crowdData.current_density);
  updateSmartPanel(crowdData);
}

function initDetailInteractions() {
  const stickyTitle = document.querySelector('[data-sticky-title]');
  const heroTitle = document.getElementById('hero-title');
  if (stickyTitle && heroTitle && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      stickyTitle.classList.toggle('visible', !entries[0].isIntersecting);
    }, { threshold: 0 });
    observer.observe(heroTitle);
  }

  const backButton = document.querySelector('[data-back-button]');
  if (backButton) {
    backButton.addEventListener('click', () => {
      if (document.referrer && document.referrer.includes(window.location.hostname)) {
        window.history.back();
      } else {
        window.location.href = 'index.html';
      }
    });
  }

  const shareButton = document.querySelector('.share-action');
  if (shareButton) {
    shareButton.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(window.location.href);
        showToast('Link copied!');
      } catch (error) {
        showToast('Unable to copy link', true);
      }
    });
  }

  const directionsButton = document.querySelector('[data-directions]');
  if (directionsButton) {
    directionsButton.addEventListener('click', () => {
      window.open('https://maps.google.com/?q=Shaniwarwada+Fort+Pune', '_blank');
    });
  }
}

function initSOSGesture() {
  const sosButton = document.querySelector('[data-sos-button]');
  if (!sosButton) return;

  const defaultText = 'EMERGENCY HELP';
  const confirmText = 'Tap again to confirm';
  let tapTimestamps = [];
  let awaitingConfirmation = false;
  let confirmTimer = null;

  function resetSOS() {
    awaitingConfirmation = false;
    sosButton.classList.remove('confirming');
    sosButton.textContent = defaultText;
    if (confirmTimer) window.clearTimeout(confirmTimer);
    confirmTimer = null;
  }

  function hideSOS() {
    sosButton.classList.remove('visible');
    resetSOS();
  }

  document.body.addEventListener('click', event => {
    if (event.target.closest('[data-sos-button]')) return;

    const now = Date.now();
    tapTimestamps = tapTimestamps.filter(timestamp => now - timestamp <= 3000);
    tapTimestamps.push(now);

    if (tapTimestamps.length >= 5) {
      tapTimestamps = [];
      resetSOS();
      sosButton.classList.add('visible');
    }
  });

  sosButton.addEventListener('click', async event => {
    event.stopPropagation();

    if (!awaitingConfirmation) {
      awaitingConfirmation = true;
      sosButton.classList.add('confirming');
      sosButton.textContent = confirmText;
      confirmTimer = window.setTimeout(resetSOS, 2000);
      return;
    }

    try {
      await postSOS('Tourist SOS triggered');
      hideSOS();
      showToast('Help alert sent to authorities');
      showAuthorityCallButton();
    } catch (error) {
      resetSOS();
      showToast('Unable to send SOS alert', true);
    }
  });
}

async function loadPageData() {
  try {
    const [crowdData, monumentData, patternData] = await Promise.all([
      fetchCrowdStatus('low_crowd'),
      fetchMonumentInfo(),
      fetchHistoricalPattern()
    ]);

    populateCrowdData(crowdData);
    populateMonumentData(monumentData);
    populatePatternData(patternData);
  } catch (error) {
    console.error('Backend fetch failed:', error);
    showErrorBanner();
    populateFallbackData();
  }
}

async function initDetailPage() {
  initDetailInteractions();
  initSOSGesture();
  await loadPageData();
  window.setInterval(() => {
    refreshDetailCrowd().catch(error => {
      console.error('Crowd refresh failed:', error);
    });
  }, 15000);
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.body.dataset.page === 'detail') {
    initDetailPage();
  } else {
    initLiveData();
  }

  document.querySelectorAll('[data-sos]').forEach(button => {
    button.addEventListener('click', async event => {
      event.preventDefault();

      try {
        await postSOS();
        showToast('SOS alert sent to authorities');
      } catch (error) {
        showToast('Unable to send SOS alert', true);
      }
    });
  });
});
