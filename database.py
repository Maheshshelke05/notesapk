from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "noteswala")
DB_PASSWORD = os.getenv("DB_PASSWORD", "mahesh")
DB_NAME = os.getenv("DB_NAME", "student_notes_app")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    google_id = Column(String(255), unique=True)
    is_premium = Column(Integer, default=0)
    premium_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = relationship("Note", back_populates="owner")
    transactions = relationship("Transaction", back_populates="buyer")

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    subject = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    file_path = Column(String(500))
    downloads = Column(Integer, default=0)
    views = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    earnings = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="notes")
    transactions = relationship("Transaction", back_populates="note")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(Integer, ForeignKey("notes.id"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    note = relationship("Note", back_populates="transactions")
    buyer = relationship("User", back_populates="transactions")

class NoteLike(Base):
    __tablename__ = "note_likes"
    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(Integer, ForeignKey("notes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('note_id', 'user_id', name='unique_like'),)

class NoteDownload(Base):
    __tablename__ = "note_downloads"
    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(Integer, ForeignKey("notes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('note_id', 'user_id', name='unique_download'),)

class NoteShare(Base):
    __tablename__ = "note_shares"
    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(Integer, ForeignKey("notes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('note_id', 'user_id', name='unique_share'),)

class CouponCode(Base):
    __tablename__ = "coupon_codes"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    days = Column(Integer, nullable=False)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created!")
    db = SessionLocal()
    try:
        if not db.query(CouponCode).filter(CouponCode.code == "mahesh").first():
            db.add(CouponCode(code="mahesh", days=1))
            db.add(CouponCode(code="PREMIUM7", days=7))
            db.add(CouponCode(code="PREMIUM30", days=30))
            db.commit()
            print("✅ Coupon codes added!")
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
