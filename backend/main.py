"""
Tamil Vedic Astrology API Server — v3.0
========================================
FastAPI backend with CORS support.
Run: uvicorn main:app --reload --port 8080
"""

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional
import os
import json
from datetime import date as dt_date
from sqlalchemy.orm import Session

from astro_engine import (
    generate_horoscope,
    calc_panchangam,
    calc_rise_set,
    calc_dasa_with_days,
    tamil_date_from_gregorian,
)

from database import engine, Base, get_db
import models
import auth
import chat_router
import admin_router
from ads_store import grouped_ads, track_ad_event

# Create DB tables
Base.metadata.create_all(bind=engine)


# ────────────────────────────────
app = FastAPI(
    title="Tamil Vedic Jyotish API",
    description="Real sidereal astrology engine with Lahiri Ayanamsa — v3.0",
    version="3.0.0",
)

_allowed_origins = [
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat_router.router)
app.include_router(admin_router.router)


# Frontend directory (one level up from backend/)
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
FRONTEND_DIR = os.path.normpath(FRONTEND_DIR)

# Mount static files at /static for explicit access
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Mount uploads directory — use Render persistent disk when available
_RENDER_DATA_DIR = "/opt/render/project/src/data"
if os.path.isdir(_RENDER_DATA_DIR):
    UPLOADS_DIR = os.path.join(_RENDER_DATA_DIR, "uploads")
else:
    UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(os.path.join(UPLOADS_DIR, "ads"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


# ────────────────────────────────
#  REQUEST / RESPONSE MODELS
# ────────────────────────────────

class HoroscopeRequest(BaseModel):
    name:     str   = Field(..., min_length=1, max_length=100, example="அருண் குமார்")
    year:     int   = Field(..., ge=1900, le=2100, example=1995)
    month:    int   = Field(..., ge=1,    le=12,   example=6)
    day:      int   = Field(..., ge=1,    le=31,   example=15)
    hour:     int   = Field(..., ge=0,    le=23,   example=10)
    minute:   int   = Field(0,   ge=0,    le=59,   example=30)
    lat:      float = Field(11.6643,  ge=-90,  le=90,  example=11.6643)
    lon:      float = Field(78.1460,  ge=-180, le=180, example=78.1460)
    timezone: float = Field(5.5,      description="UTC offset, e.g. IST=5.5")
    gender:   str   = Field("ஆண்", example="ஆண்")
    place:    Optional[str] = Field(None, example="சேலம், தமிழ்நாடு")
    father:   Optional[str] = Field(None, example="ராமன்")
    mother:   Optional[str] = Field(None, example="லட்சுமி")
    state:    Optional[str] = Field(None, example="தமிழ்நாடு")
    district: Optional[str] = Field(None, example="Salem")


class PanchangamRequest(BaseModel):
    year:  int   = Field(..., ge=1900, le=2100, example=2026)
    month: int   = Field(..., ge=1,    le=12,   example=4)
    day:   int   = Field(..., ge=1,    le=31,   example=22)
    lat:   float = Field(11.6643, ge=-90,  le=90)
    lon:   float = Field(78.1460, ge=-180, le=180)
    timezone: float = Field(5.5)


class CompatibilityRequest(BaseModel):
    person1: HoroscopeRequest
    person2: HoroscopeRequest


# ────────────────────────────────
#  ENDPOINTS
# ────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    login_page = os.path.join(FRONTEND_DIR, "login.html")
    if os.path.isfile(login_page):
        return FileResponse(login_page)
    index = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return HTMLResponse("<h2>Jyotish API v3.0 running. Go to <a href='/docs'>/docs</a></h2>")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Tamil Vedic Jyotish API v3.0", "ephem": "ok"}


def _store_horoscope_report(req: HoroscopeRequest, result: dict, db: Session, token: Optional[str] = None):
    user_id = None
    if token:
        try:
            user_id = auth.get_current_user(token, db).id
        except Exception:
            user_id = None
    try:
        report = models.AstrologyReport(
            user_id=user_id,
            report_type="horoscope",
            name=req.name,
            dob=f"{req.year}-{req.month:02d}-{req.day:02d}",
            place=req.place or "",
            rasi=(result.get("rasi") or {}).get("ta", ""),
            nakshatra=(result.get("nakshatra") or {}).get("ta", ""),
            lagna=(result.get("lagna") or {}).get("ta", ""),
            summary=(
                f"Rasi: {(result.get('rasi') or {}).get('ta', '')}; "
                f"Nakshatra: {(result.get('nakshatra') or {}).get('ta', '')}; "
                f"Lagna: {(result.get('lagna') or {}).get('ta', '')}"
            ),
            payload=json.dumps(result, ensure_ascii=False, default=str)[:200000],
        )
        db.add(report)
        db.commit()
        result["report_id"] = report.id
    except Exception:
        db.rollback()


@app.post("/api/horoscope")
async def horoscope(req: HoroscopeRequest, token: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Generate complete Tamil horoscope chart with sunrise/sunset and day-by-day dasha.
    """
    try:
        result = generate_horoscope(
            year=req.year, month=req.month, day=req.day,
            hour=req.hour, minute=req.minute,
            lat=req.lat, lon=req.lon,
            timezone_offset=req.timezone,
        )
        result["input"] = {
            "name":     req.name,
            "dob":      f"{req.year}-{req.month:02d}-{req.day:02d}",
            "time":     f"{req.hour:02d}:{req.minute:02d}",
            "place":    req.place or "",
            "gender":   req.gender,
            "father":   req.father or "",
            "mother":   req.mother or "",
            "state":    req.state or "",
            "district": req.district or "",
            "lat":      req.lat,
            "lon":      req.lon,
        }

        # Add Tamil date for birth date
        tamil_dt = tamil_date_from_gregorian(req.year, req.month, req.day)
        result["tamil_birth_date"] = tamil_dt

        # Add sunrise/sunset for birth location and birth date
        rise_set = calc_rise_set(req.year, req.month, req.day, req.lat, req.lon, req.timezone)
        result["birth_rise_set"] = rise_set

        # Add panchangam for birth date
        result["birth_panchangam"] = calc_panchangam(req.year, req.month, req.day, req.lat, req.lon, req.timezone)

        # Add today's rise/set as well
        today = dt_date.today()
        result["today_rise_set"] = calc_rise_set(
            today.year, today.month, today.day, req.lat, req.lon, req.timezone
        )

        # Add day-by-day dasha data
        dob_str  = f"{req.year}-{req.month:02d}-{req.day:02d}"
        nak_idx  = result["nakshatra"]["idx"]
        moon_deg = result["meta"]["moon_deg"]
        result["dasa_days"] = calc_dasa_with_days(dob_str, nak_idx, moon_deg)

        _store_horoscope_report(req, result, db, token=token)

        return result
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")


@app.post("/api/panchangam")
async def panchangam_post(req: PanchangamRequest):
    """Thirukkhanita Panchangam for a specific date and location."""
    try:
        return calc_panchangam(req.year, req.month, req.day, req.lat, req.lon, req.timezone)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _compatibility_score(h1: dict, h2: dict):
    score = 50
    notes = []
    r1 = h1.get("rasi") or {}
    r2 = h2.get("rasi") or {}
    l1 = h1.get("lagna") or {}
    l2 = h2.get("lagna") or {}
    n1 = h1.get("nakshatra") or {}
    n2 = h2.get("nakshatra") or {}

    distance = ((int(r2.get("num") or 1) - int(r1.get("num") or 1)) % 12) + 1
    if distance in {1, 5, 7, 9, 11}:
        score += 14
        notes.append("Moon sign distance is supportive for emotional understanding.")
    elif distance in {6, 8, 12}:
        score -= 12
        notes.append("Moon sign distance needs patience and conscious communication.")
    else:
        score += 4
        notes.append("Moon sign distance is balanced.")

    if r1.get("element") and r1.get("element") == r2.get("element"):
        score += 10
        notes.append("Both rasis share the same element, which improves rhythm.")

    if (n1.get("lord_en") or "") == (n2.get("lord_en") or ""):
        score += 10
        notes.append("Nakshatra lords match, giving similar instinctive patterns.")
    elif abs(int(n1.get("idx") or 0) - int(n2.get("idx") or 0)) <= 3:
        score += 5
        notes.append("Nakshatras are close enough to build familiarity.")

    if (l1.get("lord_en") or "") == (l2.get("lord_en") or ""):
        score += 8
        notes.append("Lagna lords align, supporting shared life direction.")

    score = max(0, min(100, score))
    verdict = "Excellent" if score >= 80 else "Good" if score >= 65 else "Moderate" if score >= 45 else "Challenging"
    return {
        "score": score,
        "verdict": verdict,
        "notes": notes,
        "factors": {
            "rasi_distance": distance,
            "person1_rasi": r1.get("ta", ""),
            "person2_rasi": r2.get("ta", ""),
            "person1_nakshatra": n1.get("ta", ""),
            "person2_nakshatra": n2.get("ta", ""),
            "person1_lagna": l1.get("ta", ""),
            "person2_lagna": l2.get("ta", ""),
        },
    }


@app.post("/api/compatibility")
async def compatibility(req: CompatibilityRequest, db: Session = Depends(get_db)):
    """Basic compatibility report from two real horoscope calculations."""
    try:
        h1 = generate_horoscope(
            year=req.person1.year, month=req.person1.month, day=req.person1.day,
            hour=req.person1.hour, minute=req.person1.minute,
            lat=req.person1.lat, lon=req.person1.lon,
            timezone_offset=req.person1.timezone,
        )
        h2 = generate_horoscope(
            year=req.person2.year, month=req.person2.month, day=req.person2.day,
            hour=req.person2.hour, minute=req.person2.minute,
            lat=req.person2.lat, lon=req.person2.lon,
            timezone_offset=req.person2.timezone,
        )
        match = _compatibility_score(h1, h2)
        result = {
            "person1": {
                "name": req.person1.name,
                "rasi": h1.get("rasi"),
                "nakshatra": h1.get("nakshatra"),
                "lagna": h1.get("lagna"),
            },
            "person2": {
                "name": req.person2.name,
                "rasi": h2.get("rasi"),
                "nakshatra": h2.get("nakshatra"),
                "lagna": h2.get("lagna"),
            },
            "compatibility": match,
            "guidance": [
                "Use this as a practical compatibility guide, not as a final marriage decision.",
                "For marriage matching, review full porutham, dosha, dasha timing, family context, and consent.",
            ],
        }
        try:
            db.add(models.AstrologyReport(
                report_type="compatibility",
                name=f"{req.person1.name} + {req.person2.name}",
                dob=f"{req.person1.year}-{req.person1.month:02d}-{req.person1.day:02d} / {req.person2.year}-{req.person2.month:02d}-{req.person2.day:02d}",
                place=f"{req.person1.place or ''} / {req.person2.place or ''}",
                rasi=f"{(h1.get('rasi') or {}).get('ta', '')} / {(h2.get('rasi') or {}).get('ta', '')}",
                nakshatra=f"{(h1.get('nakshatra') or {}).get('ta', '')} / {(h2.get('nakshatra') or {}).get('ta', '')}",
                lagna=f"{(h1.get('lagna') or {}).get('ta', '')} / {(h2.get('lagna') or {}).get('ta', '')}",
                summary=f"Compatibility score: {match['score']} ({match['verdict']})",
                payload=json.dumps(result, ensure_ascii=False, default=str)[:200000],
            ))
            db.commit()
        except Exception:
            db.rollback()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/panchangam/today")
async def panchangam_today(lat: float = 11.6643, lon: float = 78.1460, tz: float = 5.5):
    """Today's Thirukkhanita Panchangam."""
    try:
        today = dt_date.today()
        return calc_panchangam(today.year, today.month, today.day, lat, lon, tz)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cities")
async def cities():
    """Common Tamil Nadu & India city coordinates."""
    return {
        "cities": [
            {"name": "சேலம்",        "lat": 11.6643, "lon": 78.1460},
            {"name": "சென்னை",       "lat": 13.0827, "lon": 80.2707},
            {"name": "கோயம்புத்தூர்", "lat": 11.0168, "lon": 76.9558},
            {"name": "மதுரை",        "lat":  9.9252, "lon": 78.1198},
            {"name": "திருச்சி",      "lat": 10.7905, "lon": 78.7047},
            {"name": "திருநெல்வேலி", "lat":  8.7139, "lon": 77.7567},
            {"name": "ஈரோடு",        "lat": 11.3410, "lon": 77.7172},
            {"name": "வேலூர்",       "lat": 12.9165, "lon": 79.1325},
            {"name": "தஞ்சாவூர்",    "lat": 10.7870, "lon": 79.1378},
            {"name": "திருவண்ணாமலை","lat": 12.2253, "lon": 79.0747},
            {"name": "கும்பகோணம்",   "lat": 10.9617, "lon": 79.3788},
            {"name": "நாகர்கோவில்",  "lat":  8.1833, "lon": 77.4119},
            {"name": "மும்பை",       "lat": 19.0760, "lon": 72.8777},
            {"name": "டெல்லி",       "lat": 28.6139, "lon": 77.2090},
            {"name": "பெங்களூரு",    "lat": 12.9716, "lon": 77.5946},
            {"name": "ஹைதராபாத்",   "lat": 17.3850, "lon": 78.4867},
            {"name": "கொல்கத்தா",    "lat": 22.5726, "lon": 88.3639},
            {"name": "புணே",         "lat": 18.5204, "lon": 73.8567},
            {"name": "அகமதாபாத்",   "lat": 23.0225, "lon": 72.5714},
            {"name": "ஜெய்ப்பூர்",  "lat": 26.9124, "lon": 75.7873},
            {"name": "திருப்பதி",   "lat": 13.6288, "lon": 79.4192},
            {"name": "ராமேஸ்வரம்",  "lat":  9.2882, "lon": 79.3129},
            {"name": "மதுரை மீனாட்சி","lat": 9.9195, "lon": 78.1193},
            {"name": "கன்னியாகுமரி","lat":  8.0884, "lon": 77.5385},
        ]
    }

@app.get("/api/ads")
async def get_active_ads():
    """Returns active ad paths and metadata."""
    grouped = grouped_ads()
    web_ads = grouped.get("web", [])
    pdf_ads = grouped.get("pdf", [])
    banner_ads = grouped.get("banner", [])
    video_ads = grouped.get("video", [])
    all_ads = web_ads + pdf_ads + banner_ads + video_ads
    return {
        "web": web_ads[0]["path"] if web_ads else None,
        "pdf": pdf_ads[0]["path"] if pdf_ads else None,
        "banner": banner_ads[0]["path"] if banner_ads else None,
        "video": video_ads[0]["path"] if video_ads else None,
        "web_ads": web_ads,
        "pdf_ads": pdf_ads,
        "banner_ads": banner_ads,
        "video_ads": video_ads,
        "ads": all_ads,
    }


@app.post("/api/ads/{ad_id}/track")
async def track_ad(ad_id: str, request: Request, event: str = "impression", page: str = ""):
    """Track ad impressions and clicks for admin analytics."""
    tracked = track_ad_event(
        ad_id,
        event_type=event,
        page=page,
        user_agent=request.headers.get("user-agent", ""),
    )
    if not tracked:
        raise HTTPException(status_code=404, detail="Ad not found")
    return tracked

@app.get("/api/test")
async def test_chart():
    """Test endpoint — generates chart for a sample date."""
    result = generate_horoscope(
        year=1995, month=6, day=15,
        hour=10, minute=30,
        lat=11.6643, lon=78.1460,
    )
    result["input"] = {
        "name": "Test User", "dob": "1995-06-15",
        "time": "10:30", "place": "சேலம்",
        "gender": "ஆண்", "lat": 11.6643, "lon": 78.1460,
        "father": "", "mother": "", "state": "", "district": "",
    }
    result["birth_rise_set"] = calc_rise_set(1995, 6, 15, 11.6643, 78.1460)
    result["birth_panchangam"] = calc_panchangam(1995, 6, 15, 11.6643, 78.1460, 5.5)
    result["dasa_days"] = calc_dasa_with_days(
        "1995-06-15", result["nakshatra"]["idx"], result["meta"]["moon_deg"]
    )
    return result


# ────────────────────────────────
#  CATCH-ALL: Serve frontend files
#  Must be LAST so API routes take priority
# ────────────────────────────────

@app.get("/{file_path:path}")
async def serve_frontend_file(file_path: str):
    """
    Serve any file from the frontend directory.
    This allows panjangam.js, chat.js, etc. to be loaded at their natural paths.
    """
    if not file_path or file_path == "/":
        file_path = "index.html"
    if file_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    full_path = os.path.join(FRONTEND_DIR, file_path)
    full_path = os.path.normpath(full_path)
    # Security: ensure we stay within frontend directory
    if not full_path.startswith(FRONTEND_DIR):
        raise HTTPException(status_code=403, detail="Access denied")
    if os.path.isfile(full_path):
        return FileResponse(full_path)
    # Fallback to index.html for SPA routing
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="File not found")
