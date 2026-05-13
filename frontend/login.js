/**
 * JYOTISH — Login Logic v3.1
 * Handles Google Sign-In + Developer bypass with role-based routing.
 * Uses dynamic API base — no hardcoded localhost.
 */

// Dynamic API base — works when served from backend (http://localhost:8080) OR file://
const LOGIN_API = (window.resolveJyotishApiBase || (() => {
  if (window.location.protocol === 'file:') return 'http://localhost:8080';
  const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  if (isLocal && window.location.port !== '8080') return `http://${window.location.hostname}:8080`;
  return window.location.origin;
}))();
const pageUrl = window.jyotishPageUrl || ((path) => window.location.protocol === 'file:' ? path : '/' + path);

let selectedRole = 'User';

function redirectByRole(user) {
  // Store in both keys — dashboards read user_data with user_info fallback
  localStorage.setItem('user_info', JSON.stringify(user));
  localStorage.setItem('user_data', JSON.stringify(user));
  const { role, status } = user;
  if (role === 'Admin') return location.href = pageUrl('admin.html');
  if (role === 'Astrologer') {
    if (status === 'Approved') return location.href = pageUrl('astro-dashboard.html');
    return location.href = pageUrl('pending.html');
  }
  // Default: User
  location.href = pageUrl('user-dashboard.html');
}

window.onload = () => {
  const token = localStorage.getItem('auth_token');
  const ud = localStorage.getItem('user_info');
  if (token && ud) {
    try { redirectByRole(JSON.parse(ud)); } catch (e) { }
  }
};

function setRole(role) {
  selectedRole = role;
  document.getElementById('btn-user')?.classList.toggle('active', role === 'User');
  document.getElementById('btn-astro')?.classList.toggle('active', role === 'Astrologer');
  document.getElementById('tab-user')?.classList.toggle('act', role === 'User');
  document.getElementById('tab-astro')?.classList.toggle('act', role === 'Astrologer');
  const info = document.getElementById('role-info');
  if (info) {
    info.innerHTML = role === 'Astrologer'
      ? '🔮 <strong>ஜோதிடர்:</strong> Login பிறகு Admin ஒப்புதல் கிடைக்கும் வரை காத்திருக்க வேண்டும்.'
      : '👤 <strong>User:</strong> ஜாதகம் கணக்கிட்டு ஜோதிடர்களிடம் chat செய்யலாம்.';
  }
}

// Called by Google Identity Services
async function handleGoogleLogin(response) {
  const errEl = document.getElementById('error-msg') || document.getElementById('err-box');
  if (errEl) { errEl.textContent = 'Authenticating...'; errEl.style.display = 'block'; }
  try {
    const res = await fetch(`${LOGIN_API}/api/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: response.credential, role_requested: selectedRole })
    });
    const data = await res.json();
    if (res.ok) {
      localStorage.setItem('auth_token', data.access_token);
      redirectByRole(data.user);
    } else {
      if (errEl) { errEl.textContent = data.detail || 'Authentication failed.'; errEl.style.display = 'block'; }
    }
  } catch (e) {
    if (errEl) { errEl.textContent = 'Network error. Backend running? ' + LOGIN_API; errEl.style.display = 'block'; }
  }
}

async function developerBypass() {
  const errEl = document.getElementById('error-msg') || document.getElementById('err-box');
  if (errEl) { errEl.textContent = 'Simulating login...'; errEl.style.display = 'block'; }
  try {
    const res = await fetch(`${LOGIN_API}/api/auth/developer-bypass`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: 'bypass', role_requested: selectedRole })
    });
    const data = await res.json();
    if (res.ok) {
      localStorage.setItem('auth_token', data.access_token);
      redirectByRole(data.user);
    } else {
      if (errEl) { errEl.textContent = data.detail || 'Bypass failed.'; errEl.style.display = 'block'; }
    }
  } catch (e) {
    if (errEl) { errEl.textContent = 'Network error. Make sure backend is running at ' + LOGIN_API; errEl.style.display = 'block'; }
  }
}

const GOOGLE_CLIENT_ID = '1055510399803-bv8vphrhlam8cn5uljii5cs8ghubcuvl.apps.googleusercontent.com';

function selectRole(role) { setRole(role); }

async function googleLogin() {
  const errEl = document.getElementById('err-box');
  if (typeof google !== 'undefined') {
    google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: handleGoogleLogin
    });
    google.accounts.id.prompt();
  } else {
    if (errEl) { errEl.textContent = 'Google ஏற்றவில்லை. Developer Login பயன்படுத்தவும்.'; errEl.style.display = 'block'; }
  }
}

async function devLogin() {
  await developerBypass();
}