from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import json
from database import get_db
import models
from auth import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Connection Manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.online_users: set = set()

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.online_users.add(user_id)

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        self.online_users.discard(user_id)

    async def send_personal_message(self, message: str, user_id: int):
        ws = self.active_connections.get(int(user_id))
        if ws:
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(int(user_id))

    def is_online(self, user_id: int) -> bool:
        return int(user_id) in self.online_users

manager = ConnectionManager()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, db: Session = Depends(get_db)):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            receiver_id = message_data.get("receiver_id")
            content = message_data.get("content", "")
            msg_type = message_data.get("type", "text")

            # Handle typing indicator
            if msg_type == "typing":
                typing_payload = json.dumps({"type":"typing","sender_id":user_id,"receiver_id":receiver_id})
                await manager.send_personal_message(typing_payload, int(receiver_id))
                continue

            # Block harmful content (phone numbers, external links)
            blocked = False
            if content and msg_type == "text":
                lc = content.lower()
                digit_count = sum(1 for c in content if c.isdigit())
                if any(x in lc for x in ["wa.me","whatsapp","instagram.com","t.me","tiktok.com"]) or digit_count > 9:
                    content = "[BLOCKED: Phone numbers / External links are not allowed]"
                    blocked = True

            # Save to database (skip voice to DB for size)
            msg_db_content = "[voice message]" if msg_type == "voice" else content
            new_message = models.Message(
                sender_id=user_id,
                receiver_id=int(receiver_id),
                content=msg_db_content,
                msg_type=msg_type
            )
            db.add(new_message)
            db.commit()
            db.refresh(new_message)

            # For voice: send original base64 only via WS (not stored)
            send_content = content  # base64 for voice, text for text

            # Get sender info for notification
            sender = db.query(models.User).filter(models.User.id == user_id).first()
            sender_name = sender.name if sender else str(user_id)

            payload = {
                "id": new_message.id,
                "sender_id": user_id,
                "sender_name": sender_name,
                "receiver_id": int(receiver_id),
                "content": send_content,
                "type": msg_type,
                "timestamp": new_message.timestamp.isoformat()
            }

            await manager.send_personal_message(json.dumps(payload), int(receiver_id))
            # Also echo back to sender so they see delivery confirmation
            # but mark it as "echo" to prevent double-render on frontend
            echo_payload = dict(payload)
            echo_payload["echo"] = True
            await manager.send_personal_message(json.dumps(echo_payload), user_id)

    except WebSocketDisconnect:
        manager.disconnect(user_id)

# In-memory availability store (resets on server restart; use Redis in production)
astrologer_availability: Dict[int, bool] = {}

@router.get("/astrologers")
def get_astrologers(db: Session = Depends(get_db)):
    astrologers = db.query(models.User).filter(
        models.User.role == "Astrologer",
        models.User.status == "Approved"
    ).all()
    return [{
        "id": a.id,
        "name": a.name,
        "picture": a.picture or "",
        "available": astrologer_availability.get(a.id, True),
        "online": manager.is_online(a.id),
        "specialty": "Vedic Astrologer"
    } for a in astrologers]

class AvailabilityRequest(BaseModel):
    token: str
    available: bool

@router.post("/astrologer-status")
def set_astrologer_availability(req: AvailabilityRequest, db: Session = Depends(get_db)):
    from auth import get_current_user
    user = get_current_user(req.token, db)
    if user.role != "Astrologer":
        raise HTTPException(status_code=403, detail="Only astrologers can set availability")
    astrologer_availability[user.id] = req.available
    return {"available": req.available, "user_id": user.id}

@router.get("/history/{other_user_id}")
def get_chat_history(other_user_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    messages = db.query(models.Message).filter(
        ((models.Message.sender_id == user.id) & (models.Message.receiver_id == other_user_id)) |
        ((models.Message.sender_id == other_user_id) & (models.Message.receiver_id == user.id))
    ).order_by(models.Message.timestamp.asc()).all()

    # Pre-fetch sender/receiver names for the conversation
    user_ids = set()
    for m in messages:
        user_ids.add(m.sender_id)
        user_ids.add(m.receiver_id)
    users_map = {}
    if user_ids:
        users = db.query(models.User).filter(models.User.id.in_(user_ids)).all()
        for u in users:
            users_map[u.id] = u.name or u.email or f"User {u.id}"

    return [
        {
            "id": m.id,
            "sender_id": m.sender_id,
            "sender_name": users_map.get(m.sender_id, f"User {m.sender_id}"),
            "receiver_id": m.receiver_id,
            "receiver_name": users_map.get(m.receiver_id, f"User {m.receiver_id}"),
            "content": m.content,
            "type": m.msg_type,
            "timestamp": m.timestamp
        }
        for m in messages
    ]

class AIMessage(BaseModel):
    message: str
    astro_data: Optional[dict] = None

def build_jathagam_prompt(name: str, ad: dict, question: str) -> str:
    """Build a rich Vedic astrology prompt from complete jathagam data."""
    lines = [
        "You are an expert Tamil Vedic Astrologer (ஜோதிடர்) named 'AI Jyotish'.",
        "Answer ONLY in Tamil mixed with brief English terms.",
        "Always relate your answer to the person's actual planetary positions below.",
        "",
        f"═══ பயனர் விவரங்கள் (USER DETAILS) ═══",
        f"பெயர் (Name)  : {ad.get('name', name)}",
        f"பிறந்த தேதி  : {ad.get('dob', '')}  நேரம்: {ad.get('time', '')}",
        f"பிறந்த ஊர்   : {ad.get('place', '')} ({ad.get('state','')}, {ad.get('district','')})",
        f"பாலினம்      : {ad.get('gender', '')}",
        f"தந்தை பெயர்  : {ad.get('father', '')}  தாய் பெயர்: {ad.get('mother', '')}",
        "",
        f"═══ ஜாதக தகவல்கள் (JATHAGAM) ═══",
        f"ராசி (Rasi)         : {ad.get('rasi', '')} ({ad.get('rasi_en', '')})",
        f"லக்னம் (Lagna)      : {ad.get('lagna', '')} ({ad.get('lagna_en', '')}) — அதிபதி: {ad.get('lagna_lord', '')}",
        f"நட்சத்திரம்         : {ad.get('nakshatra', '')} ({ad.get('nakshatra_en', '')}) — {ad.get('pada', '')} வது பாதம்",
        f"நட்சத்திர அதிபதி   : {ad.get('nakshatra_lord', '')}",
    ]

    # Tamil Birth Date
    if ad.get('tamil_date'):
        td = ad['tamil_date']
        if isinstance(td, dict):
            lines.append(f"தமிழ் தேதி           : {td.get('year_name','')} வருடம், {td.get('month_name','')} மாதம், {td.get('day','')} நாள்")

    # Planets
    planets = ad.get('planets', [])
    if planets:
        lines.append("")
        lines.append("═══ கிரக நிலைகள் (PLANETARY POSITIONS) ═══")
        for p in planets:
            status = f" [{p.get('status','')}]" if p.get('status') else ""
            navamsa = f" D9:{p.get('navamsa','')}" if p.get('navamsa') else ""
            lines.append(f"  {p.get('name',''):<10}: {p.get('rasi',''):<12} {p.get('degree','')}{status}{navamsa}")

    # Dasha
    if ad.get('current_dasa'):
        lines.append("")
        lines.append("═══ தசா-புக்தி (DASHA-BHUKTI) ═══")
        lines.append(f"நடப்பு தசை  : {ad.get('current_dasa', '')}")
        lines.append(f"நடப்பு புக்தி: {ad.get('current_bhukti', '')}")
        if ad.get('dasa_days_remaining'):
            lines.append(f"புக்தி மீதம் : {ad.get('dasa_days_remaining', '')}")
        if ad.get('dasa_remaining'):
            lines.append(f"தசா மீதம்   : {ad.get('dasa_remaining', '')} வருடங்கள்")
        if ad.get('all_dashas'):
            lines.append(f"அனைத்து தசைகள்: {ad.get('all_dashas','')}")

    # Birth Panchangam
    if ad.get('birth_tithi'):
        lines.append("")
        lines.append("═══ பிறப்பு பஞ்சாங்கம் (BIRTH PANCHANGAM) ═══")
        lines.append(f"திதி    : {ad.get('birth_tithi','')}")
        lines.append(f"வாரம்   : {ad.get('birth_vara','')}")
        lines.append(f"யோகம்   : {ad.get('birth_yoga','')}")
        lines.append(f"கரணம்   : {ad.get('birth_karana','')}")
        lines.append(f"ராகு காலம்: {ad.get('birth_rahu_kalam','')}")

    # Sunrise at birth
    if ad.get('sunrise'):
        lines.append(f"சூரிய உதயம் : {ad.get('sunrise','')}  அஸ்தமனம்: {ad.get('sunset','')}")
        lines.append(f"சந்திர உதயம்: {ad.get('moonrise','')}  அஸ்தமனம்: {ad.get('moonset','')}")

    # Today's Panchangam
    if ad.get('today_tithi'):
        lines.append("")
        lines.append("═══ இன்றைய பஞ்சாங்கம் (TODAY PANCHANGAM) ═══")
        lines.append(f"திதி   : {ad.get('today_tithi','')}")
        lines.append(f"வாரம்  : {ad.get('today_vara','')}")
        lines.append(f"நட்சத்திரம்: {ad.get('today_nakshatra','')}")
        lines.append(f"யோகம்  : {ad.get('today_yoga','')}")
        lines.append(f"ராகு காலம்: {ad.get('today_rahu_kalam','')}")
        lines.append(f"சூரியன்: {ad.get('today_sunrise','')} — {ad.get('today_sunset','')}")

    lines.append("")
    lines.append(f"═══ பயனர் கேள்வி (USER QUESTION) ═══")
    lines.append(f"{question}")
    lines.append("")
    lines.append("மேலே உள்ள ஜாதக தகவல்களை வைத்து, கேள்விக்கு விரிவாக, தமிழில் பதில் அளிக்கவும்.")
    lines.append("பதிலில் கிரக நிலைகள், தசை, நட்சத்திரம், ராசி ஆகியவற்றை குறிப்பிடவும்.")
    lines.append("பதில் friendly, encouraging மற்றும் accurate ஆக இருக்கட்டும். Emojis சேர்க்கவும்.")

    return "\n".join(lines)


def smart_fallback(name: str, question: str, ad: dict) -> str:
    """Rich rule-based fallback using actual jathagam data."""
    q = question.lower()
    rasi     = ad.get('rasi', '')
    nak      = ad.get('nakshatra', '')
    nak_en   = ad.get('nakshatra_en', '')
    lagna    = ad.get('lagna', '')
    ll       = ad.get('lagna_lord', '')
    dasa     = ad.get('current_dasa', '')
    bhukti   = ad.get('current_bhukti', '')
    days_rem = ad.get('dasa_days_remaining', '')
    planets  = ad.get('planets', [])

    planet_str = ''
    if planets:
        planet_str = '\n'.join([f"  • {p.get('name','')}: {p.get('rasi','')} {p.get('degree','')}{' ('+p.get('status','')+')' if p.get('status') else ''}"
                                 for p in planets])

    today_pj = ''
    if ad.get('today_tithi'):
        today_pj = f"\n\n📅 **இன்றைய பஞ்சாங்கம்**:\nதிதி: {ad.get('today_tithi')} · வாரம்: {ad.get('today_vara')} · நட்சத்திரம்: {ad.get('today_nakshatra')}\nயோகம்: {ad.get('today_yoga')} · ராகு காலம்: {ad.get('today_rahu_kalam')}\n☀ {ad.get('today_sunrise','')} — 🌇 {ad.get('today_sunset','')}"

    base = f"வணக்கம் {name}! 🙏\n\n"

    if 'திருமண' in q or 'marriage' in q or 'கல்யாண' in q:
        p_guru = next((p for p in planets if 'குரு' in p.get('name','') or 'Guru' in p.get('name','')), None)
        guru_info = f"குரு {p_guru['rasi']}-ல் உள்ளார்." if p_guru else ''
        return base + f"💍 **திருமண யோகம்**:\n\nஉங்கள் ராசி **{rasi}**, லக்னம் **{lagna}** ({ll} அதிபதி). {guru_info}\n\nதற்போது **{dasa}** தசையில் **{bhukti}** புக்தி நடக்கிறது. {days_rem}\n\nதிருமண நேரம் குரு, சுக்கிர தசா/புக்தி மற்றும் 7ஆம் வீட்டு அதிபதி பலத்தை பொறுத்து அமையும். விரைவில் நல்ல செய்தி வரும்! ✨"

    if 'பண' in q or 'money' in q or 'வருமான' in q or 'finance' in q:
        return base + f"💰 **பண யோகம்**:\n\nராசி: **{rasi}**, நட்சத்திரம்: **{nak}**\nதசை: **{dasa}** → புக்தி: **{bhukti}** {days_rem}\n\n11ஆம் வீடு (லாப ஸ்தானம்) மற்றும் புதன், சுக்கிர நிலைகளை வைத்து பண யோகம் அமையும். {dasa} தசையில் முயற்சிகள் பலன் தரும். நம்பிக்கையோடு இருங்கள்! 🌟"

    if 'உடல்' in q or 'health' in q or 'நோய்' in q or 'உடல்நலம்' in q:
        return base + f"💪 **உடல் நலம்**:\n\nலக்னம்: **{lagna}**, ராசி: **{rasi}**\nதசை: **{dasa}**, புக்தி: **{bhukti}**\n\nலக்னாதிபதி {ll} நல்ல நிலையில் இருந்தால் உடல் நலம் சீராக இருக்கும். 6ஆம் வீட்டு அதிபதி நிலையை கவனிக்க வேண்டும். ஆரோக்கியமான உணவு மற்றும் யோகாவை பின்பற்றுங்கள்! 🧘"

    if 'வேலை' in q or 'job' in q or 'career' in q or 'தொழில்' in q:
        return base + f"💼 **தொழில் / வேலை**:\n\nராசி: **{rasi}**, நட்சத்திரம்: **{nak}**\nதசை: **{dasa}** → புக்தி: **{bhukti}** {days_rem}\n\n10ஆம் வீடு (தொழில் ஸ்தானம்) மற்றும் சனி, சூரியன் நிலைகளை வைத்து தொழில் வளர்ச்சி தெரியும். {dasa} தசையில் புதிய வாய்ப்புகள் வரலாம்! 🚀"

    if 'பஞ்சாங்கம்' in q or 'panchangam' in q or 'இன்று' in q or 'today' in q:
        if today_pj:
            return base + "📅 **இன்றைய திருக்கணித பஞ்சாங்கம்**:" + today_pj

    # General response with full data
    p_info = f"\n\n🪐 **கிரக நிலைகள்**:\n{planet_str}" if planet_str else ""
    dasa_info = f"\n\n⏳ **தசை**: {dasa} → **புக்தி**: {bhukti}" + (f" ({days_rem})" if days_rem else "")
    pj_info = today_pj

    return (base +
            f"**ஜாதக சுருக்கம்**:\n🌙 ராசி: **{rasi}** | ⬆ லக்னம்: **{lagna}** | ⭐ நட்சத்திரம்: **{nak}**"
            + dasa_info + p_info + pj_info +
            f"\n\n📌 கேள்வி: \"{question}\"\n\n" +
            "உங்கள் ஜாதகத்தை வைத்து விரிவான பலன்களுக்கு Gemini API Key அல்லது Ollama LLM இணைக்கவும். "
            "தற்போதைய கிரக நிலைகள் உங்களுக்கு சாதகமாக உள்ளன! ✨🌟")


@router.post("/ai")
def chat_with_ai(data: AIMessage, token: str = Query(...), db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    ad = data.astro_data or {}
    name = ad.get("name", user.name) or user.name

    # Build rich prompt
    prompt = build_jathagam_prompt(name, ad, data.message)

    return _generate_ai_response(name, data.message, ad, prompt)

@router.post("/ai-public")
def chat_with_ai_public(data: AIMessage, db: Session = Depends(get_db)):
    ad = data.astro_data or {}
    name = ad.get("name", "User")

    # Build rich prompt
    prompt = build_jathagam_prompt(name, ad, data.message)
    
    return _generate_ai_response(name, data.message, ad, prompt)

def _generate_ai_response(name, message, ad, prompt):
    reply = ""

    # 1. Try Local Ollama LLM only when explicitly enabled. The client can block
    # for a long time if no local Ollama server/model is responding.
    try:
        import os
        if os.environ.get("ENABLE_OLLAMA") == "1" or os.environ.get("OLLAMA_HOST"):
            import ollama
            model_name = os.environ.get("OLLAMA_MODEL", "llama3")
            res = ollama.chat(model=model_name, messages=[{"role": "user", "content": prompt}])
            reply = res["message"]["content"]
    except Exception:
        reply = ""

    # 2. Try Google Gemini if a key is configured.
    if not reply:
        try:
            import google.generativeai as genai
            import os
            api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("No API Key")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            res = model.generate_content(prompt)
            reply = res.text
        except Exception:
            # 3. Smart rule-based fallback with real data
            reply = smart_fallback(name, message, ad)

    return {"reply": reply}



@router.get("/contacts")
def get_contacts(token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    # If astrologer, get users they chatted with
    # If user, get astrologers they chatted with
    messages = db.query(models.Message).filter(
        (models.Message.sender_id == user.id) | (models.Message.receiver_id == user.id)
    ).all()
    
    contact_ids = set()
    for m in messages:
        if m.sender_id != user.id:
            contact_ids.add(m.sender_id)
        if m.receiver_id != user.id:
            contact_ids.add(m.receiver_id)
            
    contacts = db.query(models.User).filter(models.User.id.in_(contact_ids)).all()
    return [
        {
            "id": c.id,
            "name": c.name or c.email or f"User {c.id}",
            "email": c.email or "",
            "picture": c.picture or "",
            "role": c.role or "User",
        }
        for c in contacts
    ]