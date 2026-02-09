from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum

Base = declarative_base()

class UserRole(str, enum.Enum):
    NORMAL = "normal"
    PREMIUM = "premium"
    ADMIN = "admin"

class BookStatus(str, enum.Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    SOLD = "sold"
    EXPIRED = "expired"

class BookCondition(str, enum.Enum):
    NEW = "new"
    LIKE_NEW = "like_new"
    GOOD = "good"
    FAIR = "fair"

class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    google_id = Column(String(255), unique=True, index=True, nullable=False)
    profile_picture = Column(String(500))
    role = Column(Enum(UserRole), default=UserRole.NORMAL, nullable=False)
    is_blocked = Column(Boolean, default=False)
    ai_messages_today = Column(Integer, default=0)
    ai_messages_reset_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")
    books = relationship("Book", back_populates="user", cascade="all, delete-orphan")
    login_logs = relationship("LoginLog", back_populates="user", cascade="all, delete-orphan")
    note_likes = relationship("NoteLike", back_populates="user", cascade="all, delete-orphan")
    note_downloads = relationship("NoteDownload", back_populates="user", cascade="all, delete-orphan")
    chat_logs = relationship("ChatLog", back_populates="user", cascade="all, delete-orphan")
    book_requests_made = relationship("BookBuyRequest", foreign_keys="BookBuyRequest.buyer_id", back_populates="buyer")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class LoginLog(Base):
    __tablename__ = "login_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ip_address = Column(String(45))
    device_info = Column(Text)
    login_time = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="login_logs")
    
    __table_args__ = (Index('idx_user_login', 'user_id', 'login_time'),)

class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(500), unique=True, nullable=False)
    blacklisted_at = Column(DateTime, default=datetime.utcnow)

class Note(Base):
    __tablename__ = "notes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    subject = Column(String(100), nullable=False)
    description = Column(Text)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    downloads = Column(Integer, default=0)
    views = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    earnings = Column(Float, default=0.0)
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="notes")
    note_likes = relationship("NoteLike", back_populates="note", cascade="all, delete-orphan")
    note_downloads = relationship("NoteDownload", back_populates="note", cascade="all, delete-orphan")
    
    __table_args__ = (Index('idx_subject_created', 'subject', 'created_at'),)

class NoteLike(Base):
    __tablename__ = "note_likes"
    
    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    note = relationship("Note", back_populates="note_likes")
    user = relationship("User", back_populates="note_likes")
    
    __table_args__ = (Index('idx_note_user_like', 'note_id', 'user_id', unique=True),)

class NoteDownload(Base):
    __tablename__ = "note_downloads"
    
    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ip_address = Column(String(45))
    device_info = Column(Text)
    view_duration = Column(Integer, default=0)
    is_earning_counted = Column(Boolean, default=False)
    downloaded_at = Column(DateTime, default=datetime.utcnow)
    
    note = relationship("Note", back_populates="note_downloads")
    user = relationship("User", back_populates="note_downloads")
    
    __table_args__ = (Index('idx_note_user_download', 'note_id', 'user_id'),)

class Book(Base):
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    condition = Column(Enum(BookCondition), nullable=False)
    price = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_name = Column(String(255))
    status = Column(Enum(BookStatus), default=BookStatus.AVAILABLE, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="books")
    images = relationship("BookImage", back_populates="book", cascade="all, delete-orphan")
    buy_requests = relationship("BookBuyRequest", back_populates="book", cascade="all, delete-orphan")
    
    __table_args__ = (Index('idx_status_location', 'status', 'latitude', 'longitude'),)

class BookImage(Base):
    __tablename__ = "book_images"
    
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    image_path = Column(String(500), nullable=False)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    book = relationship("Book", back_populates="images")

class BookBuyRequest(Base):
    __tablename__ = "book_buy_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    full_name = Column(String(255), nullable=False)
    mobile_number = Column(String(15), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_name = Column(String(255))
    message = Column(Text)
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    book = relationship("Book", back_populates="buy_requests")
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="book_requests_made")
    
    __table_args__ = (Index('idx_book_buyer', 'book_id', 'buyer_id'),)

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="notifications")
    
    __table_args__ = (Index('idx_user_read', 'user_id', 'is_read'),)

class ChatLog(Base):
    __tablename__ = "chat_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="chat_logs")
    
    __table_args__ = (Index('idx_user_chat_date', 'user_id', 'created_at'),)

class AbuseReport(Base):
    __tablename__ = "abuse_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reported_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    content_type = Column(String(50))
    content_id = Column(Integer)
    reason = Column(Text, nullable=False)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

# Database connection and session management
from config import get_settings

settings = get_settings()
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database - create all tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
