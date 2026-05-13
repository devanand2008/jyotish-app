/**
 * JYOTISH — Private Astrologer Chat System
 * Real-time WebSocket Messaging with Backend Database
 */

// Dynamic API base — works when served from backend (http://localhost:8080) OR opened as file://
const CHAT_API_BASE = (window.resolveJyotishApiBase || (() => {
    if (window.location.protocol === 'file:') return 'http://localhost:8080';
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (isLocal && window.location.port !== '8080') return `http://${window.location.hostname}:8080`;
    return window.location.origin;
}))();

let currentChatUserId = null;
let currentChatUserName = "";
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let recordingTimer = null;
let recordingSeconds = 0;
let ws = null;

// Auth Tokens
let authToken = localStorage.getItem("auth_token");
let currentUser = JSON.parse(localStorage.getItem("user_data") || localStorage.getItem("user_info") || "null");

function initAuthUI() {
    if (!currentUser) {
        drawLoginOverlay();
    } else if (currentUser.status === "Pending") {
        drawPendingOverlay();
    } else if (currentUser.role === "Admin") {
        drawAdminOverlay();
    }
}

function drawLoginOverlay() {
    const overlay = document.createElement("div");
    overlay.id = "auth-overlay";
    overlay.style.cssText = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(8,6,15,0.95);z-index:9999;display:flex;align-items:center;justify-content:center;";
    overlay.innerHTML = `
        <div style="background:#16132A;padding:40px;border-radius:12px;text-align:center;border:1px solid #322C58;max-width:350px;width:100%;">
            <h1 style="color:#C8A84B;font-family:serif;margin-bottom:10px;">Jyotish Login</h1>
            <p style="color:#6A6090;margin-bottom:20px;font-size:14px;">Sign in securely to chat.</p>
            <select id="login-role" style="width:100%;padding:10px;margin-bottom:20px;border-radius:8px;background:#1E1A35;color:white;border:1px solid #322C58;">
                <option value="User">Login as User</option>
                <option value="Astrologer">Apply as Astrologer</option>
            </select>
            <div id="g_id_onload"
                data-client_id="1055510399803-bv8vphrhlam8cn5uljii5cs8ghubcuvl.apps.googleusercontent.com" 
                data-context="signin"
                data-ux_mode="popup"
                data-callback="handleGoogleCallback"
                data-auto_prompt="false">
            </div>
            <div class="g_id_signin"
                data-type="standard"
                data-shape="rectangular"
                data-theme="filled_black"
                data-text="signin_with"
                data-size="large"
                data-logo_alignment="left">
            </div>
            <button onclick="document.getElementById('auth-overlay').remove()" style="margin-top:20px;background:none;border:none;color:#mut;cursor:pointer;font-size:12px;">Close (Continue without chat)</button>
        </div>
    `;
    document.body.appendChild(overlay);
}

function drawPendingOverlay() {
    const overlay = document.createElement("div");
    overlay.id = "auth-overlay";
    overlay.style.cssText = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(8,6,15,0.95);z-index:9999;display:flex;align-items:center;justify-content:center;";
    overlay.innerHTML = `
        <div style="background:#16132A;padding:40px;border-radius:12px;text-align:center;border:1px solid #322C58;max-width:400px;width:100%;">
            <h2 style="color:#E8C96A;margin-bottom:15px;">Waiting for Approval</h2>
            <p style="color:#6A6090;line-height:1.6;">Hello <strong>${currentUser.name}</strong>, your astrologer account is under review.</p>
            <button onclick="localStorage.clear();window.location.reload();" style="margin-top:20px;padding:8px 16px;background:transparent;border:1px solid #E04B4A;color:#E04B4A;border-radius:8px;cursor:pointer;">Sign Out</button>
        </div>
    `;
    document.body.appendChild(overlay);
}

function drawAdminOverlay() {
    const div = document.createElement("div");
    div.id = "admin-dashboard-btn";
    div.style.cssText = "position:fixed;bottom:80px;right:20px;z-index:999;background:var(--red);color:white;padding:10px 20px;border-radius:20px;cursor:pointer;font-weight:bold;box-shadow:0 4px 12px rgba(0,0,0,0.5);";
    div.innerText = "Admin Panel";
    div.onclick = openAdminPanel;
    document.body.appendChild(div);
}

async function openAdminPanel() {
    const overlay = document.createElement("div");
    overlay.id = "admin-panel-overlay";
    overlay.style.cssText = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(8,6,15,0.98);z-index:9999;overflow-y:auto;padding:40px 20px;";

    try {
        const res = await fetchWithAuth('/api/admin/astrologers');
        let rows = '';
        res.forEach(a => {
            rows += `
                <tr style="border-bottom:1px solid #322C58;">
                    <td style="padding:10px;">${a.name}</td>
                    <td style="padding:10px;">${a.email}</td>
                    <td style="padding:10px;">${a.status}</td>
                    <td style="padding:10px;">
                        ${a.status === 'Pending' ? `
                            <button onclick="adminAction(${a.id}, 'approve')" style="background:#1D8C68;color:white;border:none;padding:5px 10px;border-radius:4px;cursor:pointer;margin-right:5px;">✅ Approve</button>
                            <button onclick="adminAction(${a.id}, 'reject')" style="background:#E04B4A;color:white;border:none;padding:5px 10px;border-radius:4px;cursor:pointer;">Reject</button>
                        ` : ''}
                    </td>
                </tr>
            `;
        });

        overlay.innerHTML = `
            <div style="max-width:800px;margin:0 auto;background:#16132A;padding:20px;border-radius:12px;border:1px solid #322C58;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
                    <h2 style="color:#C8A84B;">Admin Dashboard</h2>
                    <button onclick="document.getElementById('admin-panel-overlay').remove()" style="background:none;border:1px solid white;color:white;padding:5px 15px;border-radius:8px;cursor:pointer;">Close</button>
                </div>
                <table style="width:100%;text-align:left;color:white;border-collapse:collapse;">
                    <tr style="background:#100E1E;"><th style="padding:10px;">Name</th><th style="padding:10px;">Email</th><th style="padding:10px;">Status</th><th style="padding:10px;">Actions</th></tr>
                    ${rows}
                </table>
            </div>
        `;
        document.body.appendChild(overlay);
    } catch (e) { alert("Failed to load admin panel"); }
}

async function adminAction(id, action) {
    await fetchWithAuth(`/api/admin/astrologers/${id}/${action}`, { method: 'POST' });
    if (action === 'approve') {
        showNotification('✅ ஜோதிடர் Approved! அவர்கள் தானாகவே Dashboard-க்கு redirect ஆவார்கள்.');
    } else {
        showNotification('❌ ஜோதிடர் Rejected.');
    }
    document.getElementById('admin-panel-overlay').remove();
    openAdminPanel();
}

window.handleGoogleCallback = async function (response) {
    const role = document.getElementById('login-role')?.value || 'User';
    try {
        const res = await fetch(`${CHAT_API_BASE}/api/auth/google`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: response.credential, role_requested: role })
        });
        const data = await res.json();
        if (res.ok) {
            localStorage.setItem('auth_token', data.access_token);
            localStorage.setItem('user_info', JSON.stringify(data.user));
            window.location.reload();
        } else alert("Login failed: " + data.detail);
    } catch (e) { console.error(e); alert("Network Error"); }
};

document.addEventListener('DOMContentLoaded', initAuthUI);

/* ── WebSocket Connection ── */
function connectWebSocket() {
    if (!currentUser) return;
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
    if (ws) ws.close();

    // Connect to WebSocket server — derive WS URL from CHAT_API_BASE
    const wsUrl = CHAT_API_BASE.replace(/^http/, 'ws') + `/api/chat/ws/${currentUser.id}`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => console.log("WebSocket connected");
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        // Skip echo-back from server — we render sent messages optimistically
        if (data.echo === true) return;
        // If the message belongs to the current open chat, render it
        if (currentChatUserId && data.sender_id === currentChatUserId) {
            appendMessage(data);
        } else if (data.sender_id !== currentUser.id) {
            // Show notification for messages from other chats
            showNotification("💬 New message from " + (data.sender_name || "User"));
        }
    };
    ws.onclose = () => {
        console.log("WebSocket disconnected. Reconnecting in 3s...");
        setTimeout(connectWebSocket, 3000);
    };
}

if (currentUser) connectWebSocket();

/* ── API Helpers ── */
async function fetchWithAuth(url, options = {}) {
    if (!authToken) return null;
    // Prepend API base to relative URLs (e.g. "/api/chat/history/...")
    const fullUrl = new URL(url.startsWith('/') ? CHAT_API_BASE + url : url, CHAT_API_BASE);
    if (!fullUrl.searchParams.has('token')) {
        fullUrl.searchParams.set('token', authToken);
    }
    const headers = {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json',
        ...(options.headers || {})
    };
    const res = await fetch(fullUrl.toString(), { ...options, headers });
    if (res.status === 401) {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("user_info");
        window.location.reload();
        return null;
    }
    const contentType = res.headers.get('content-type') || '';
    const body = contentType.includes('application/json') ? await res.json() : await res.text();
    if (!res.ok) {
        throw new Error((body && body.detail) || body || `API ${res.status}`);
    }
    return body;
}

/* ── Open Chat Box ── */
async function openChat(otherUserId, otherUserName) {
    currentChatUserId = otherUserId;
    currentChatUserName = otherUserName;

    const overlay = document.getElementById('chat-overlay');
    const title = document.getElementById('chat-astro-name');
    const status = document.querySelector('.chat-astro-status');

    if (overlay) overlay.style.display = 'flex';
    if (title) title.textContent = '💬 ' + otherUserName;
    if (status) status.innerHTML = otherUserId === 'AI' ? '✨ Instant AI Responses' : '🟢 Online · Private Chat · No WhatsApp shared';

    // Load History
    if (otherUserId === 'AI') {
        let msgs = [];
        try {
            msgs = JSON.parse(localStorage.getItem('ai_chat_history') || '[]');
        } catch (e) {
            console.error(e);
            localStorage.setItem('ai_chat_history', '[]');
        }
        renderMessages(msgs);
    } else {
        const msgs = await fetchWithAuth(`/api/chat/history/${otherUserId}?token=${authToken}`);
        renderMessages(msgs || []);
    }

    const inp = document.getElementById('chat-input');
    if (inp) inp.focus();
}

function openAIChat() {
    openChat('AI', 'AI Astrologer');
}

function closeChat() {
    currentChatUserId = null;
    const overlay = document.getElementById('chat-overlay');
    if (overlay) overlay.style.display = 'none';
    stopRecording();
}

/* ── Render Messages ── */
function renderMessages(msgs) {
    const box = document.getElementById('chat-messages');
    if (!box) return;

    if (!msgs.length) {
        box.innerHTML = `<div style="text-align:center;color:var(--mut);padding:30px 10px;font-size:12px;">
            <div style="font-size:28px;margin-bottom:8px;">🔮</div>
            Start a secure private conversation.<br>
            <small style="font-size:10px;">Messages are end-to-end encrypted.</small>
        </div>`;
        return;
    }

    box.innerHTML = '';
    msgs.forEach(m => appendMessage(m, false));
    box.scrollTop = box.scrollHeight;
}

function appendMessage(m, scroll = true) {
    const box = document.getElementById('chat-messages');
    if (!box) return;

    // Remove empty state message if it's the first message
    if (box.innerHTML.includes("Start a secure private conversation")) {
        box.innerHTML = '';
    }

    const isUser = m.sender_id === currentUser.id;
    const dateObj = new Date(m.timestamp);
    const time = dateObj.toLocaleTimeString('ta-IN', { hour: '2-digit', minute: '2-digit' });
    const dateStr = dateObj.toLocaleDateString('ta-IN', { day: '2-digit', month: 'short' });

    let content = '';
    if (m.type === 'voice') {
        content = `<audio controls src="${m.content}" style="max-width:180px;height:32px;"></audio>
            <div style="font-size:9px;color:var(--mut);margin-top:3px;">🎙 Voice Message</div>`;
    } else {
        content = `<div style="white-space:pre-wrap;line-height:1.6;">${escHtml(m.content)}</div>`;
    }

    const html = `<div class="msg-bubble ${isUser ? 'sent' : 'recv'}">
        <div class="msg-content">
            ${content}
        </div>
        <div class="msg-time">${dateStr} · ${time}</div>
    </div>`;

    box.insertAdjacentHTML('beforeend', html);
    if (scroll) box.scrollTop = box.scrollHeight;
}

function escHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/* ── Send Text Message ── */
async function sendChatMessage() {
    if (!currentChatUserId) return;

    const inp = document.getElementById('chat-input');
    const text = (inp?.value || '').trim();
    if (!text) return;

    if (currentChatUserId === 'AI') {
        const msg = { sender_id: currentUser.id, receiver_id: 'AI', content: text, type: "text", timestamp: new Date().toISOString() };
        appendMessage(msg);

        let history = JSON.parse(localStorage.getItem('ai_chat_history') || '[]');
        history.push(msg);

        inp.value = '';

        // Fetch AI Response from Backend
        try {
            let astroData = null;
            if (typeof CD !== 'undefined' && Object.keys(CD).length > 0) {
                astroData = CD;
            }

            const aiUrl = authToken
                ? `${CHAT_API_BASE}/api/chat/ai?token=${encodeURIComponent(authToken)}`
                : `${CHAT_API_BASE}/api/chat/ai-public`;
            const res = await fetch(aiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    astro_data: astroData
                })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || `API ${res.status}`);

            const aiMsg = { sender_id: 'AI', receiver_id: currentUser.id, content: data.reply, type: "text", timestamp: new Date().toISOString() };
            appendMessage(aiMsg);
            history.push(aiMsg);
            localStorage.setItem('ai_chat_history', JSON.stringify(history));
        } catch (e) {
            console.error("AI Chat Error:", e);
        }
        return;
    }

    // Optimistically render the sent message immediately
    const sentMsg = {
        sender_id: currentUser.id,
        receiver_id: currentChatUserId,
        content: text,
        type: "text",
        timestamp: new Date().toISOString()
    };
    appendMessage(sentMsg);
    inp.value = '';

    if (!ws || ws.readyState !== WebSocket.OPEN) {
        showNotification('⚠ இணைப்பு இல்லை. மீண்டும் முயற்சிக்கிறது...');
        connectWebSocket();
        return;
    }

    const payload = {
        receiver_id: currentChatUserId,
        content: text,
        type: "text"
    };

    ws.send(JSON.stringify(payload));
}

/* ── Voice Recording ── */
async function toggleVoiceRecord() {
    if (isRecording) {
        stopRecording();
    } else {
        await startRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = [];
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
        mediaRecorder.onstop = () => {
            const blob = new Blob(audioChunks, { type: 'audio/webm' });
            const reader = new FileReader();
            reader.onloadend = () => {
                if (currentChatUserId && ws && ws.readyState === WebSocket.OPEN) {
                    const payload = {
                        receiver_id: currentChatUserId,
                        content: reader.result, // base64
                        type: "voice"
                    };
                    ws.send(JSON.stringify(payload));
                }
            };
            reader.readAsDataURL(blob);
            stream.getTracks().forEach(t => t.stop());
        };

        mediaRecorder.start();
        isRecording = true;
        recordingSeconds = 0;
        updateRecordBtn(true);

        recordingTimer = setInterval(() => {
            recordingSeconds++;
            const btn = document.getElementById('voice-record-btn');
            if (btn) btn.textContent = `⏹ ${recordingSeconds}s`;
            if (recordingSeconds >= 60) stopRecording(); // max 60s
        }, 1000);

    } catch (e) {
        alert('Microphone access denied. Please allow microphone permission.');
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        clearInterval(recordingTimer);
        updateRecordBtn(false);
    }
}

function updateRecordBtn(recording) {
    const btn = document.getElementById('voice-record-btn');
    if (!btn) return;
    if (recording) {
        btn.textContent = `⏹ ${recordingSeconds}s`;
        btn.style.background = 'var(--red)';
        btn.style.animation = 'pulse 1s ease-in-out infinite';
    } else {
        btn.textContent = '🎙';
        btn.style.background = 'var(--acc)';
        btn.style.animation = 'none';
    }
}

function chatKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
    }
}

function showNotification(msg) {
    // Basic toast
    const toast = document.createElement('div');
    toast.textContent = msg;
    toast.style.cssText = "position:fixed;bottom:20px;right:20px;background:var(--acc);color:#fff;padding:10px 20px;border-radius:8px;z-index:9999;font-size:12px;";
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

/* ── Load Approved Astrologers for Users ── */
async function loadAstrologers() {
    const astroCards = document.getElementById('astro-cards');
    if (!astroCards || !authToken || currentUser?.role !== 'User') return;

    try {
        const res = await fetch(`${CHAT_API_BASE}/api/chat/astrologers`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const astros = await res.json();

        let aiBotHtml = `
            <div class="chat-astro-btn" onclick="startPublicVideoCall()" style="border-color: var(--gold); background: linear-gradient(135deg, rgba(200, 168, 75, 0.1), rgba(232, 201, 106, 0.1)); border-radius: 12px; margin-bottom: 12px;">
                <div class="cab-avatar" style="background: linear-gradient(135deg, var(--gold), var(--gold2)); color: black;">📞</div>
                <div style="flex:1;">
                    <div class="cab-name" style="color: var(--gold); font-weight: bold;">Public Video Consultation</div>
                    <div class="cab-spec" style="color: var(--mut); font-size: 11px;">Connect to any available astrologer</div>
                </div>
                <div class="cab-badge" style="background: var(--gold); color: black;">▶</div>
            </div>
            <div class="chat-astro-btn" onclick="window.location.href='ai-chat.html'" style="border-color: var(--teal); background: linear-gradient(135deg, rgba(26, 173, 160, 0.1), rgba(29, 140, 104, 0.1)); border-radius: 12px; margin-bottom: 12px;">
                <div class="cab-avatar" style="background: linear-gradient(135deg, var(--teal), var(--green)); color: white;">🤖</div>
                <div style="flex:1;">
                    <div class="cab-name" style="color: var(--teal); font-weight: bold;">AI Astrologer</div>
                    <div class="cab-spec" style="color: var(--mut); font-size: 11px;">Free AI Chat & Predictions</div>
                </div>
                <div class="cab-badge" style="background: var(--teal); color: white;">✨</div>
            </div>
        `;

        if (astros.length === 0) {
            astroCards.innerHTML = aiBotHtml + `
                <div style="text-align:center;color:var(--mut);padding:30px;width:100%;">
                    <div style="font-size:30px;margin-bottom:8px;">🔮</div>
                    <div>தற்போது ஜோதிடர்கள் இல்லை.<br><small>விரைவில் இணைவார்கள்</small></div>
                </div>
            `;
            return;
        }

        let html = aiBotHtml;
        astros.forEach(a => {
            html += `
                <div class="chat-astro-btn" onclick="openChat(${a.id}, '${escHtml(a.name)}')">
                    <div class="cab-avatar">🔮</div>
                    <div style="flex:1;">
                        <div class="cab-name">${escHtml(a.name)}</div>
                        <div class="cab-spec">Private Chat (Online)</div>
                    </div>
                    <div class="cab-badge">💬</div>
                </div>
            `;
        });
        astroCards.innerHTML = html;

        // Update the screen titles to reflect the new system
        const sAstrologers = document.getElementById('s-astrologers');
        if (sAstrologers) {
            const h = sAstrologers.querySelector('.sec-s');
            if (h) h.textContent = "Secure Private Chat Consultation";
        }

    } catch (e) {
        console.error("Failed to load astrologers", e);
    }
}

// Ensure astrologers load when app starts
if (currentUser) {
    connectWebSocket();
    setTimeout(loadAstrologers, 1000);
}