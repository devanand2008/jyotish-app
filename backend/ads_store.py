import json
import os
import shutil
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func

from database import SessionLocal
import models


AD_TYPES = {"web", "pdf", "banner", "video"}
ALLOWED_EXTS = {
    "web": {"jpg", "jpeg", "png", "webp", "gif", "mp4", "webm", "ogg"},
    "pdf": {"jpg", "jpeg", "png", "webp"},
    "banner": {"jpg", "jpeg", "png", "webp", "gif"},
    "video": {"mp4", "webm", "ogg", "mov"},
}

_RENDER_DATA_DIR = "/opt/render/project/src/data"
if os.path.isdir(_RENDER_DATA_DIR):
    _UPLOAD_ROOT = os.path.join(_RENDER_DATA_DIR, "uploads")
else:
    _UPLOAD_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")

ADS_DIR = os.path.join(_UPLOAD_ROOT, "ads")
LEGACY_MANIFEST_PATH = os.path.join(ADS_DIR, "ads_manifest.json")


def _ensure_dir():
    os.makedirs(ADS_DIR, exist_ok=True)


def _public_path(filename):
    return f"/uploads/ads/{filename}"


def _safe_ext(filename):
    ext = os.path.splitext(filename or "")[1].lower().strip(".")
    return ext or "bin"


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _is_scheduled(ad, now=None):
    now = now or datetime.utcnow()
    if ad.starts_at and ad.starts_at > now:
        return False
    if ad.ends_at and ad.ends_at < now:
        return False
    return True


def _serialize_ad(ad, impressions=0, clicks=0):
    return {
        "id": ad.id,
        "type": ad.type,
        "path": ad.path,
        "filename": ad.filename,
        "original_name": ad.original_name,
        "mime_type": ad.mime_type or "",
        "size": int(ad.size or 0),
        "title": ad.title or "",
        "placement": ad.placement or "all",
        "target_pages": ad.target_pages or "all",
        "click_url": ad.click_url or "",
        "enabled": ad.enabled is not False,
        "non_skippable": ad.non_skippable is not False,
        "starts_at": ad.starts_at.isoformat() + "Z" if ad.starts_at else None,
        "ends_at": ad.ends_at.isoformat() + "Z" if ad.ends_at else None,
        "created_at": ad.created_at.isoformat() + "Z" if ad.created_at else None,
        "updated_at": ad.updated_at.isoformat() + "Z" if ad.updated_at else None,
        "impressions": int(impressions or 0),
        "clicks": int(clicks or 0),
    }


def _legacy_ads():
    _ensure_dir()
    found = []

    if os.path.isfile(LEGACY_MANIFEST_PATH):
        try:
            with open(LEGACY_MANIFEST_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            source = raw.get("ads", raw if isinstance(raw, list) else [])
            for ad in source:
                if isinstance(ad, dict) and ad.get("type") in AD_TYPES and ad.get("path"):
                    found.append(ad)
        except Exception:
            pass

    for filename in os.listdir(ADS_DIR):
        if filename == os.path.basename(LEGACY_MANIFEST_PATH):
            continue
        for ad_type in AD_TYPES:
            if filename.startswith(f"{ad_type}_ad."):
                path = os.path.join(ADS_DIR, filename)
                found.append({
                    "id": f"legacy-{ad_type}-{os.path.splitext(filename)[1].lstrip('.') or 'file'}",
                    "type": ad_type,
                    "path": _public_path(filename),
                    "filename": filename,
                    "original_name": filename,
                    "mime_type": "",
                    "size": os.path.getsize(path),
                    "enabled": True,
                    "non_skippable": True,
                    "created_at": datetime.utcfromtimestamp(os.path.getmtime(path)).isoformat() + "Z",
                })
    return found


def _ensure_legacy_imported(db):
    if db.query(models.Ad).first():
        return
    for raw in _legacy_ads():
        ad_type = raw.get("type")
        if ad_type not in AD_TYPES:
            continue
        ad_id = str(raw.get("id") or uuid.uuid4().hex[:10])
        if db.query(models.Ad).filter(models.Ad.id == ad_id).first():
            continue
        db.add(models.Ad(
            id=ad_id,
            type=ad_type,
            path=raw.get("path") or "",
            filename=raw.get("filename") or os.path.basename(raw.get("path", "")),
            original_name=raw.get("original_name") or raw.get("filename") or os.path.basename(raw.get("path", "")),
            mime_type=raw.get("mime_type") or "",
            size=int(raw.get("size") or 0),
            title=raw.get("title") or "",
            placement=raw.get("placement") or "all",
            target_pages=raw.get("target_pages") or "all",
            click_url=raw.get("click_url") or "",
            enabled=raw.get("enabled") is not False,
            non_skippable=True,
            starts_at=_parse_dt(raw.get("starts_at")),
            ends_at=_parse_dt(raw.get("ends_at")),
            created_at=_parse_dt(raw.get("created_at")) or datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))
    db.commit()


def _open_session(db=None):
    if db is not None:
        return db, False
    return SessionLocal(), True


def read_ads(include_disabled=False, db=None):
    db, should_close = _open_session(db)
    try:
        _ensure_legacy_imported(db)
        ads = db.query(models.Ad).order_by(models.Ad.created_at.desc()).all()
        event_counts = {
            (ad_id, event_type): count
            for ad_id, event_type, count in (
                db.query(models.AdEvent.ad_id, models.AdEvent.event_type, func.count(models.AdEvent.id))
                .group_by(models.AdEvent.ad_id, models.AdEvent.event_type)
                .all()
            )
        }
        results = []
        for ad in ads:
            if not include_disabled and (ad.enabled is False or not _is_scheduled(ad)):
                continue
            impressions = event_counts.get((ad.id, "impression"), 0)
            clicks = event_counts.get((ad.id, "click"), 0)
            results.append(_serialize_ad(ad, impressions=impressions, clicks=clicks))
        return results
    finally:
        if should_close:
            db.close()


def write_ads(ads):
    db = SessionLocal()
    try:
        existing = {ad.id: ad for ad in db.query(models.Ad).all()}
        keep_ids = set()
        for raw in ads:
            if not isinstance(raw, dict) or raw.get("type") not in AD_TYPES or not raw.get("path"):
                continue
            ad_id = str(raw.get("id") or uuid.uuid4().hex[:10])
            keep_ids.add(ad_id)
            ad = existing.get(ad_id) or models.Ad(id=ad_id)
            ad.type = raw.get("type")
            ad.path = raw.get("path")
            ad.filename = raw.get("filename") or os.path.basename(raw.get("path"))
            ad.original_name = raw.get("original_name") or ad.filename
            ad.mime_type = raw.get("mime_type") or ""
            ad.size = int(raw.get("size") or 0)
            ad.title = raw.get("title") or ""
            ad.placement = raw.get("placement") or "all"
            ad.target_pages = raw.get("target_pages") or "all"
            ad.click_url = raw.get("click_url") or ""
            ad.enabled = raw.get("enabled") is not False
            ad.non_skippable = True
            ad.starts_at = _parse_dt(raw.get("starts_at"))
            ad.ends_at = _parse_dt(raw.get("ends_at"))
            ad.created_at = _parse_dt(raw.get("created_at")) or datetime.utcnow()
            ad.updated_at = datetime.utcnow()
            db.merge(ad)
        for ad_id, ad in existing.items():
            if ad_id not in keep_ids:
                db.delete(ad)
        db.commit()
        return read_ads(include_disabled=True, db=db)
    finally:
        db.close()


def add_uploaded_ad(
    ad_type,
    upload_file,
    title: str = "",
    placement: str = "all",
    target_pages: str = "all",
    click_url: str = "",
    starts_at: Optional[str] = None,
    ends_at: Optional[str] = None,
):
    if ad_type not in AD_TYPES:
        raise ValueError("Invalid ad type")
    ext = _safe_ext(upload_file.filename)
    if ext not in ALLOWED_EXTS[ad_type]:
        raise ValueError(f"Invalid file type for {ad_type} ad")

    _ensure_dir()
    ad_id = uuid.uuid4().hex[:12]
    filename = f"{ad_type}_{ad_id}.{ext}"
    path = os.path.join(ADS_DIR, filename)
    with open(path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    size = os.path.getsize(path) if os.path.isfile(path) else 0
    now = datetime.utcnow()
    ad = models.Ad(
        id=ad_id,
        type=ad_type,
        path=_public_path(filename),
        filename=filename,
        original_name=upload_file.filename or filename,
        mime_type=upload_file.content_type or "",
        size=size,
        title=title or "",
        placement=placement or "all",
        target_pages=target_pages or "all",
        click_url=click_url or "",
        enabled=True,
        non_skippable=True,
        starts_at=_parse_dt(starts_at),
        ends_at=_parse_dt(ends_at),
        created_at=now,
        updated_at=now,
    )

    db = SessionLocal()
    try:
        db.add(ad)
        db.commit()
        db.refresh(ad)
        return _serialize_ad(ad)
    finally:
        db.close()


def remove_ads(ad_type=None, ad_id=None):
    db = SessionLocal()
    removed = []
    try:
        q = db.query(models.Ad)
        if ad_id:
            q = q.filter(models.Ad.id == str(ad_id))
        elif ad_type:
            q = q.filter(models.Ad.type == ad_type)
        else:
            return []
        rows = q.all()
        for ad in rows:
            removed.append(_serialize_ad(ad))
            db.delete(ad)
        db.commit()
    finally:
        db.close()

    for ad in removed:
        filename = os.path.basename(ad.get("path", ""))
        if not filename:
            continue
        file_path = os.path.join(ADS_DIR, filename)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
    return removed


def set_ad_enabled(ad_id, enabled):
    return update_ad(ad_id, {"enabled": bool(enabled)})


def update_ad(ad_id, fields):
    allowed = {
        "title", "placement", "target_pages", "click_url", "enabled",
        "starts_at", "ends_at", "non_skippable",
    }
    db = SessionLocal()
    try:
        ad = db.query(models.Ad).filter(models.Ad.id == str(ad_id)).first()
        if not ad:
            return None
        for key, value in (fields or {}).items():
            if key not in allowed:
                continue
            if key in {"starts_at", "ends_at"}:
                setattr(ad, key, _parse_dt(value))
            elif key == "enabled":
                setattr(ad, key, bool(value))
            elif key == "non_skippable":
                setattr(ad, key, True)
            else:
                setattr(ad, key, value or "")
        ad.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(ad)
        return _serialize_ad(ad)
    finally:
        db.close()


def track_ad_event(ad_id, event_type="impression", page="", user_agent=""):
    event_type = event_type if event_type in {"impression", "click"} else "impression"
    db = SessionLocal()
    try:
        ad = db.query(models.Ad).filter(models.Ad.id == str(ad_id)).first()
        if not ad:
            return None
        event = models.AdEvent(
            ad_id=ad.id,
            event_type=event_type,
            page=(page or "")[:120],
            user_agent=(user_agent or "")[:500],
        )
        db.add(event)
        db.commit()
        return {"ad_id": ad.id, "event_type": event_type, "tracked": True}
    finally:
        db.close()


def ad_performance():
    db = SessionLocal()
    try:
        ads = read_ads(include_disabled=True, db=db)
        return {
            "ads": ads,
            "totals": {
                "impressions": sum(ad.get("impressions", 0) for ad in ads),
                "clicks": sum(ad.get("clicks", 0) for ad in ads),
                "active_ads": sum(1 for ad in ads if ad.get("enabled")),
                "scheduled_ads": sum(1 for ad in ads if ad.get("starts_at") or ad.get("ends_at")),
            },
        }
    finally:
        db.close()


def grouped_ads(include_disabled=False):
    ads = read_ads(include_disabled=include_disabled)
    grouped = {ad_type: [] for ad_type in AD_TYPES}
    for ad in ads:
        grouped.setdefault(ad["type"], []).append(ad)
    return grouped
