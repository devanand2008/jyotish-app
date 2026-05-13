/**
 * JYOTISH - Ads Manager (Frontend)
 * Loads multiple active ads from /api/ads and injects compact, non-skippable
 * in-page placements into designated content gaps.
 */

const _ADS_BASE = (window.resolveJyotishApiBase || (() => {
  if (window.location.protocol === 'file:') return 'http://localhost:8080';
  const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  if (isLocal && window.location.port !== '8080') return `http://${window.location.hostname}:8080`;
  return window.location.origin;
}))();

const ADS_API = _ADS_BASE + '/api/ads';
const ADS_LS_KEY = 'jyotish_ads';

let activeAds = {
  web: [],
  pdf: [],
  banner: [],
  video: [],
  web_enabled: true,
  pdf_enabled: true,
  banner_enabled: true,
  video_enabled: true
};

function adSrc(ad) {
  if (!ad) return null;
  if (typeof ad === 'string') return ad;
  return ad.src || ad.path || ad.data || null;
}

function absolutizeAdPath(src) {
  if (!src || typeof src !== 'string') return null;
  if (/^(data:|https?:|blob:)/i.test(src)) return src;
  return _ADS_BASE + (src.startsWith('/') ? src : '/' + src);
}

function normalizeAd(ad, type) {
  const src = absolutizeAdPath(adSrc(ad));
  if (!src) return null;
  if (typeof ad === 'string') {
    return { id: src, type, src, non_skippable: true, enabled: true };
  }
  return {
    id: String(ad.id || src),
    type: ad.type || type,
    src,
    title: ad.title || ad.original_name || ad.filename || 'Advertisement',
    mime_type: ad.mime_type || '',
    click_url: ad.click_url || '',
    placement: ad.placement || 'all',
    target_pages: ad.target_pages || 'all',
    enabled: ad.enabled !== false,
    non_skippable: true,
    created_at: ad.created_at || ''
  };
}

function uniqueAds(list) {
  const seen = new Set();
  return list.filter(ad => {
    const key = ad.id || ad.src;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function normalizeServerList(data, type) {
  const listKey = `${type}_ads`;
  let list = [];
  if (Array.isArray(data?.[listKey])) list = list.concat(data[listKey]);
  if (Array.isArray(data?.[type])) list = list.concat(data[type]);
  else if (data?.[type]) list.push(data[type]);
  return uniqueAds(list.map(ad => normalizeAd(ad, type)).filter(Boolean));
}

function normalizeLocalItems(d, type) {
  const items = [];
  if (Array.isArray(d[`${type}_items`])) {
    d[`${type}_items`].forEach(item => {
      if (item && item.active !== false && item.enabled !== false) {
        items.push(normalizeAd({
          id: item.id,
          type,
          data: item.data || item.src,
          title: item.name,
          enabled: true
        }, type));
      }
    });
  }
  if (d[`${type}_data`]) {
    items.push(normalizeAd({
      id: `${type}-legacy-local`,
      type,
      data: d[`${type}_data`],
      title: d[`${type}_name`] || 'Local Advertisement'
    }, type));
  }
  return uniqueAds(items.filter(Boolean));
}

async function loadAds() {
  activeAds.web = [];
  activeAds.pdf = [];
  activeAds.banner = [];
  activeAds.video = [];

  try {
    const res = await fetch(ADS_API);
    if (res.ok) {
      const data = await res.json();
      activeAds.web = normalizeServerList(data, 'web');
      activeAds.pdf = normalizeServerList(data, 'pdf');
      activeAds.banner = normalizeServerList(data, 'banner');
      activeAds.video = normalizeServerList(data, 'video');
    }
  } catch (e) {
    // Local fallback is applied below.
  }

  const lsAds = localStorage.getItem(ADS_LS_KEY);
  if (lsAds) {
    try {
      const d = JSON.parse(lsAds);
      if (d.web_enabled !== undefined) activeAds.web_enabled = d.web_enabled;
      if (d.pdf_enabled !== undefined) activeAds.pdf_enabled = d.pdf_enabled;
      if (d.banner_enabled !== undefined) activeAds.banner_enabled = d.banner_enabled;
      if (d.video_enabled !== undefined) activeAds.video_enabled = d.video_enabled;
      activeAds.web = uniqueAds(activeAds.web.concat(normalizeLocalItems(d, 'web')));
      activeAds.pdf = uniqueAds(activeAds.pdf.concat(normalizeLocalItems(d, 'pdf')));
      activeAds.banner = uniqueAds(activeAds.banner.concat(normalizeLocalItems(d, 'banner')));
      activeAds.video = uniqueAds(activeAds.video.concat(normalizeLocalItems(d, 'video')));
    } catch(e) {}
  }

  renderAds();
}

function getAd(type, index) {
  const list = activeAds[type] || [];
  if (!list.length) return null;
  return list[index % list.length];
}

function renderAds() {
  const bannerEnabled = activeAds.banner_enabled !== false && activeAds.web_enabled !== false;
  const webEnabled = activeAds.web_enabled !== false;
  const videoEnabled = activeAds.video_enabled !== false && activeAds.web_enabled !== false;
  renderSlot('ad-slot-top', bannerEnabled ? (getAd('banner', 0) || getAd('web', 0)) : null, 'top');
  renderSlot('ad-slot-mid', webEnabled ? (videoEnabled ? (getAd('video', 0) || getAd('web', 1)) : getAd('web', 1)) : null, 'mid');
  renderSlot('ad-slot-bottom', webEnabled ? (getAd('web', 2) || (videoEnabled ? getAd('video', 1) : null)) : null, 'bottom');
  renderSlot('ad-slot-pj', webEnabled ? (getAd('web', 3) || (videoEnabled ? getAd('video', 2) : null)) : null, 'pj');
  renderBannerSlot('ad-banner-main', bannerEnabled ? getAd('banner', 0) : null);
}

function renderBannerSlot(slotId, ad) {
  renderSlot(slotId, ad, 'banner');
}

function isVideoAd(ad) {
  const src = adSrc(ad) || '';
  const mime = typeof ad === 'object' ? (ad.mime_type || '') : '';
  return /video\//i.test(mime) || /\.(mp4|webm|ogg)(\?|#|$)/i.test(src) || /^data:video\//i.test(src);
}

function escapeAttr(value) {
  return String(value || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
}

function trackJyotishAd(adId, eventType, page) {
  if (!adId || /^data:|^blob:/i.test(adId)) return;
  const url = `${_ADS_BASE}/api/ads/${encodeURIComponent(adId)}/track?event=${encodeURIComponent(eventType || 'impression')}&page=${encodeURIComponent(page || '')}`;
  try {
    if (navigator.sendBeacon) {
      navigator.sendBeacon(url, new Blob([], { type: 'application/json' }));
      return;
    }
  } catch(e) {}
  try { fetch(url, { method: 'POST', keepalive: true }); } catch(e) {}
}

function wireAdTracking(el, ad, page) {
  if (!ad || !ad.id) return;
  if (!/^data:|^blob:/i.test(ad.src || '')) {
    trackJyotishAd(ad.id, 'impression', page);
  }
  if (ad.click_url) {
    const wrap = el.querySelector('.ad-wrap');
    if (wrap) {
      wrap.style.cursor = 'pointer';
      wrap.addEventListener('click', () => {
        if (!/^data:|^blob:/i.test(ad.src || '')) trackJyotishAd(ad.id, 'click', page);
        window.open(ad.click_url, '_blank', 'noopener');
      }, { once: false });
    }
  }
}

function renderSlot(slotId, ad, type) {
  const el = document.getElementById(slotId);
  if (!el) return;
  const src = adSrc(ad);
  if (!src) {
    el.classList.remove('show');
    el.innerHTML = '';
    return;
  }

  el.classList.add('show');
  const label = type === 'banner' ? 'Sponsored' : 'Advertisement';
  const title = escapeAttr(ad.title || 'Advertisement');
  if (isVideoAd(ad)) {
    el.innerHTML = `
      <div class="ad-wrap" data-non-skippable="true" data-ad-id="${escapeAttr(ad.id)}" title="${title}">
        <span class="ad-label">${label}</span>
        <video autoplay muted loop playsinline class="ad-media"><source src="${src}"></video>
      </div>`;
  } else {
    el.innerHTML = `
      <div class="ad-wrap" data-non-skippable="true" data-ad-id="${escapeAttr(ad.id)}" title="${title}">
        <span class="ad-label">${label}</span>
        <img src="${src}" class="ad-media" alt="Advertisement" loading="lazy"/>
      </div>`;
  }
  wireAdTracking(el, ad, type);
}

function getPdfAdSrc() {
  if (activeAds.pdf_enabled === false) return null;
  const ad = getAd('pdf', 0);
  return adSrc(ad);
}

function saveLocalAd(type, dataUrl) {
  const stored = localStorage.getItem(ADS_LS_KEY);
  const d = stored ? JSON.parse(stored) : {};
  const items = Array.isArray(d[`${type}_items`]) ? d[`${type}_items`] : [];
  items.push({
    id: `${type}-${Date.now()}`,
    data: dataUrl,
    name: 'Local Advertisement',
    active: true,
    non_skippable: true,
    date: new Date().toISOString()
  });
  d[`${type}_items`] = items;
  d[`${type}_data`] = dataUrl;
  localStorage.setItem(ADS_LS_KEY, JSON.stringify(d));
  loadAds();
}

function setAdEnabled(type, enabled) {
  const stored = localStorage.getItem(ADS_LS_KEY);
  const d = stored ? JSON.parse(stored) : {};
  d[type + '_enabled'] = enabled;
  localStorage.setItem(ADS_LS_KEY, JSON.stringify(d));
  activeAds[type + '_enabled'] = enabled;
  renderAds();
}

function removeLocalAd(type) {
  const stored = localStorage.getItem(ADS_LS_KEY);
  const d = stored ? JSON.parse(stored) : {};
  delete d[type + '_data'];
  delete d[`${type}_items`];
  localStorage.setItem(ADS_LS_KEY, JSON.stringify(d));
  activeAds[type] = [];
  renderAds();
}

window.renderJyotishAds = renderAds;
window.reloadJyotishAds = loadAds;
window.getPdfAdSrc = getPdfAdSrc;
window.trackJyotishAd = trackJyotishAd;

document.addEventListener('DOMContentLoaded', () => { loadAds(); });
