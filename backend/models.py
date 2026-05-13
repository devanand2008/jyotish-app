from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    picture = Column(String, nullable=True)
    role = Column(String, default="User") # "User", "Astrologer", "Admin"
    status = Column(String, default="Approved") # "Approved", "Pending", "Rejected"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    messages_sent = relationship("Message", foreign_keys="[Message.sender_id]", back_populates="sender")
    messages_received = relationship("Message", foreign_keys="[Message.receiver_id]", back_populates="receiver")

class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    astrologer_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    messages = relationship("Message", back_populates="chat_room")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id"), nullable=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    content = Column(String)
    msg_type = Column(String, default="text") # text, voice
    timestamp = Column(DateTime, default=datetime.utcnow)

    chat_room = relationship("ChatRoom", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="messages_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="messages_received")


class Ad(Base):
    __tablename__ = "ads"

    id = Column(String, primary_key=True, index=True)
    type = Column(String, index=True)  # web, pdf, banner, video
    path = Column(String)
    filename = Column(String)
    original_name = Column(String)
    mime_type = Column(String, default="")
    size = Column(Integer, default=0)
    title = Column(String, default="")
    placement = Column(String, default="all")
    target_pages = Column(String, default="all")  # comma-separated page keys
    click_url = Column(String, default="")
    enabled = Column(Boolean, default=True)
    non_skippable = Column(Boolean, default=True)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    events = relationship("AdEvent", back_populates="ad", cascade="all, delete-orphan")


class AdEvent(Base):
    __tablename__ = "ad_events"

    id = Column(Integer, primary_key=True, index=True)
    ad_id = Column(String, ForeignKey("ads.id"), index=True)
    event_type = Column(String, index=True)  # impression, click
    page = Column(String, default="")
    user_agent = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    ad = relationship("Ad", back_populates="events")


class AstrologyReport(Base):
    __tablename__ = "astrology_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    report_type = Column(String, default="horoscope", index=True)
    name = Column(String, default="")
    dob = Column(String, default="")
    place = Column(String, default="")
    rasi = Column(String, default="")
    nakshatra = Column(String, default="")
    lagna = Column(String, default="")
    summary = Column(Text, default="")
    payload = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class AstrologyContent(Base):
    __tablename__ = "astrology_content"

    id = Column(Integer, primary_key=True, index=True)
    content_type = Column(String, default="article", index=True)
    title = Column(String)
    body = Column(Text, default="")
    language = Column(String, default="ta")
    status = Column(String, default="draft", index=True)  # draft, published
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.utcnow)
