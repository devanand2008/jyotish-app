# 🔮 JYOTISH 3.0 — Tamil Vedic Astrology Platform

<div align="center">

![JYOTISH Banner](https://img.shields.io/badge/JYOTISH-3.0-gold?style=for-the-badge&logo=stars&labelColor=1a0a2e)
![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Google OAuth](https://img.shields.io/badge/Google_OAuth-2.0-4285F4?style=for-the-badge&logo=google&logoColor=white)
![WebSocket](https://img.shields.io/badge/WebSocket-Live_Chat-purple?style=for-the-badge)

**A full-stack Tamil Vedic astrology platform with real-time chat, AI horoscope readings, live Panchangam, and a complete admin ecosystem — built with FastAPI + Vanilla JS.**

</div>

---

## ✨ What is JYOTISH 3.0?

JYOTISH 3.0 is a production-ready **Tamil Vedic Astrology web application** that combines ancient astrological wisdom with modern web technology. It generates accurate **Sidereal horoscope charts** using the **Lahiri Ayanamsa** system, provides daily **Thirukkhanita Panchangam**, and connects users with live astrologers through a real-time **WebSocket chat system** — all in Tamil.

---

## 🌟 Core Features

### 🪐 Astrology Engine
- **Full Sidereal Horoscope Chart** — Rasi, Lagna, Navamsa charts using real astronomical ephemeris (`ephem` library)
- **Lahiri Ayanamsa** calculation (true Vedic sidereal system)
- **All 9 Planetary Positions** — Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu with degrees, signs, and status (exalted/debilitated/retrograde)
- **27 Nakshatras** with Pada, lord, and deity
- **Vimshottari Dasha System** — Full dasha-bhukti timeline with day-by-day calculations
- **Tamil Birth Date** — Converted to Tamil calendar (Year name, Month, Day)
- **Thirukkhanita Panchangam** — Tithi, Vara, Nakshatra, Yoga, Karana, Rahu Kalam, sunrise/sunset/moonrise/moonset
- **Multiple Cities** — 24 Tamil Nadu & India cities with precise coordinates

### 👤 User Authentication & Roles
- **Google OAuth 2.0** Sign-In (works on desktop & mobile)
- **3 Role System:**
  | Role | Access |
  |------|--------|
  | **User** | View horoscope, chat with astrologers, AI readings |
  | **Astrologer** | Accept consultations, set availability, chat with users |
  | **Admin** | Full platform control (reserved for `devanand2008@gmail.com`) |
- **JWT Authentication** (7-day tokens) via `python-jose`
- **Astrologer Approval Flow** — New astrologers await admin approval before going live
- **Pending Page** — Astrologers see their approval status in real time

### 💬 Real-Time Chat System
- **WebSocket-based** live messaging (instant delivery)
- **Text + Voice Messages** — Users can send recorded voice notes
- **Typing Indicators** — Live "typing..." display
- **Online Presence** — See which astrologers are currently online
- **Chat History** — Full message history persisted in SQLite
- **Content Moderation** — Automatically blocks phone numbers, WhatsApp links, and external social media URLs to keep communication on-platform
- **Contact List** — Auto-populated from chat history

### 🤖 AI Horoscope Advisor
- **Personalized AI Readings** in **Tamil language** based on actual jathagam data
- **Multi-LLM Support:**
  - 🟢 **Google Gemini 1.5 Flash** (when API key configured)
  - 🟠 **Ollama / Local LLM** (when `ENABLE_OLLAMA=1`)
  - 🔵 **Smart Rule-Based Fallback** (works without any AI API) — gives meaningful Tamil answers about marriage, money, health, career based on real planetary data
- Includes full planetary positions, dasha-bhukti, and panchangam in the AI prompt

### 🛡️ Admin Panel
- **Dashboard Stats** — Total users, astrologers, messages
- **User Management** — View all registered users, approve/reject/suspend accounts
- **Astrologer Management** — One-click approve or reject pending astrologers
- **Advertisement System:**
  - Upload and manage **Web Ads**, **PDF Ads**, **Banner Ads**, **Video Ads**
  - Enable/disable individual ads without deleting
  - Ads served via `/api/ads` endpoint
- **Excel Export** — Download all user data as a styled `.xlsx` report with:
  - Color-coded status (Approved=Green, Pending=Yellow, Rejected=Red)
  - Messages sent/received per user
  - Summary sheet with platform statistics

### 📅 Panchangam (Daily Almanac)
- Real-time **Thirukkhanita Panchangam** for any date and location
- **Today's Panchangam** API endpoint with auto-detected date
- Full data: Tithi, Nakshatra, Yoga, Karana, Sunrise/Sunset, Rahu Kalam, Gulika Kalam

---

## 🏗️ Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| **FastAPI** | REST API + WebSocket server |
| **SQLAlchemy + SQLite** | Database ORM & storage |
| **Uvicorn** | ASGI server |
| **ephem** | Swiss ephemeris for planetary calculations |
| **google-auth** | Google OAuth token verification |
| **python-jose** | JWT token generation & validation |
| **passlib** | Password hashing |
| **openpyxl** | Excel report generation |
| **Pydantic v2** | Request/response validation |

### Frontend
| Technology | Purpose |
|---|---|
| **Vanilla HTML/CSS/JS** | No framework — pure, fast, lightweight |
| **Google Identity Services** | OAuth 2.0 sign-in button |
| **WebSocket API** | Real-time chat |
| **MediaRecorder API** | Voice message recording |
| **LocalStorage** | Auth token & settings persistence |

---

## 📁 Project Structure

```
jyotish-app/
├── index.html                    ← GitHub Pages entry (redirects to frontend)
├── frontend/
│   ├── login.html                ← Google Sign-In page
│   ├── login.js / login.css      ← Auth logic & styles
│   ├── index.html                ← Main horoscope app (chart generation)
│   ├── astro-dashboard.html      ← Astrologer's workspace
│   ├── user-dashboard.html       ← User's personal dashboard
│   ├── admin.html                ← Admin control panel
│   ├── pending.html              ← Astrologer approval waiting page
│   ├── ai-chat.html              ← AI Tamil astrology advisor
│   ├── api-base.js               ← Smart backend URL resolver
│   ├── chat.js                   ← WebSocket chat engine
│   ├── ads.js                    ← Advertisement display logic
│   └── panjangam.js              ← Panchangam widget
└── backend/
    ├── main.py                   ← FastAPI app entry point
    ├── astro_engine.py           ← 1800+ line Vedic calculation engine
    ├── auth.py                   ← Google OAuth + JWT auth
    ├── chat_router.py            ← WebSocket + AI chat endpoints
    ├── admin_router.py           ← Admin management + Excel export
    ├── ads_store.py              ← Advertisement store
    ├── models.py                 ← SQLAlchemy database models
    ├── database.py               ← DB connection setup
    └── requirements.txt          ← Python dependencies
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.10+
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR-USERNAME/jyotish-app.git
cd jyotish-app
```

### 2. Set Up Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

### 3. Start the Server
```bash
uvicorn main:app --reload --port 8080
```

### 4. Open the App
```
http://localhost:8080
```

That's it! The backend serves both the API **and** the frontend files.

---

## 🌐 Deployment (GitHub Pages + Local Backend)

The frontend is hosted on **GitHub Pages** (free, always online).  
The backend runs on **your laptop** and connects when started.

```
GitHub Pages (Frontend) ──── API calls ────► Your Laptop (Backend :8080)
     Always online                              Online when you start it
```

### Set the backend URL from any browser:
```javascript
// Run this in browser console on the GitHub Pages site
setJyotishBackend("http://localhost:8080")
```

For internet access from anywhere, use **ngrok**:
```bash
ngrok http 8080
# Then in browser console:
setJyotishBackend("https://YOUR-NGROK-URL.ngrok-free.app")
```

---

## ⚙️ Configuration

### Google OAuth
Set your Google Client ID in `backend/auth.py`:
```python
GOOGLE_CLIENT_ID = "YOUR-GOOGLE-CLIENT-ID.apps.googleusercontent.com"
```

### AI (Optional)
Set environment variables to enable AI features:
```bash
# Google Gemini
set GOOGLE_API_KEY=your_gemini_api_key

# OR Local Ollama LLM
set ENABLE_OLLAMA=1
set OLLAMA_MODEL=llama3
```

Without any API key, the app uses a built-in smart Tamil rule-based system.

### Admin Account
The admin email is locked to: `devanand2008@gmail.com`  
This account automatically gets Admin role and full access upon sign-in.

---

## 🔐 Security Features

- All admin routes verified by both JWT role AND email
- Phone numbers and social media links auto-blocked in chat
- JWT tokens expire after 7 days
- CORS configured for cross-origin frontend access
- File upload validation for advertisements

---

## 📸 App Flow

```
Login (Google OAuth)
    │
    ├── User Role ──────────── User Dashboard
    │                              └── Generate Horoscope Chart
    │                              └── Chat with Astrologers (WebSocket)
    │                              └── AI Tamil Advisor
    │
    ├── Astrologer Role ─────── Astrologer Dashboard (after admin approval)
    │                              └── Accept consultations
    │                              └── Set availability (Online/Busy)
    │                              └── Chat with Users
    │
    └── Admin Role ─────────── Admin Panel
                                   └── Approve/Reject Astrologers
                                   └── Manage Users
                                   └── Upload Advertisements
                                   └── Export User Data (Excel)
                                   └── View Platform Stats
```

---

## 📜 License

Built with ❤️ for Tamil astrology — traditional wisdom, modern technology.

**Developer:** Devanand S  
**Contact:** devanand2008@gmail.com

---

## Production Deployment Notes

### Recommended Hosting
Use **Render paid Web Service (Starter or higher)** for the complete app. This repo is configured so one FastAPI service serves both:

- Backend APIs and WebSockets
- Frontend HTML/CSS/JS
- Uploaded ad files from persistent storage
- SQLite database on a Render persistent disk

Render free web services can spin down when idle, so `render.yaml` uses `plan: starter` to keep the service available continuously.

### Render Setup

1. Push the full repository to GitHub.
2. In Render, choose **New > Blueprint** and connect the GitHub repository.
3. Render reads `render.yaml` and creates the `jyotish-astro-app` service.
4. Set or confirm these environment variables:
   - `SECRET_KEY`
   - `GOOGLE_CLIENT_ID`
   - `ADMIN_EMAIL`
   - `ALLOWED_ORIGINS`
5. Add the deployed Render URL to Google OAuth authorized JavaScript origins and redirect URLs.
6. Open the Render service URL. The backend serves the frontend directly, so the API base is same-origin.

For the exact fields to paste into Render, open:

```text
RENDER_FORM_VALUES.txt
```

For the full step-by-step deployment checklist, open:

```text
RENDER_DEPLOY_STEPS.md
```

### Mobile Google Login Fix

If mobile login shows `Error 400: redirect_uri_mismatch`, add this exact URL in Google Cloud OAuth **Authorized redirect URIs**:

```text
https://jyotish-astro-app.onrender.com/google-mobile-callback.html
```

If your Render service URL is different, replace `jyotish-astro-app.onrender.com` with your actual Render domain.

### Admin Access
The email in `ADMIN_EMAIL` automatically receives Admin role after Google login. Default:

```text
devanand2008@gmail.com
```

### New Production Features

- Database-backed ad metadata with banner, poster, PDF and video ads.
- Ad scheduling with start/end times.
- Per-ad enable/disable without deleting files.
- Ad impression and click tracking.
- Stored horoscope and compatibility report records.
- Admin analytics, content management, settings and report dashboard.
- Compatibility report page at `/compatibility.html`.

### GitHub Push

```bash
git add .
git commit -m "Build production astrology app features"
git push origin main
```
