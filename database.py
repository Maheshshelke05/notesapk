from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, inspect
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

def init_db():
    """Initialize database and auto-migrate missing columns"""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Auto-migrate missing columns
        inspector = inspect(engine)
        
        # Check notes table columns
        if inspector.has_table("notes"):
            existing_columns = [col['name'] for col in inspector.get_columns('notes')]
            required_columns = ['views', 'shares', 'likes', 'earnings']
            
            with engine.connect() as conn:
                for col in required_columns:
                    if col not in existing_columns:
                        if col == 'earnings':
                            conn.execute(f"ALTER TABLE notes ADD COLUMN {col} FLOAT DEFAULT 0")
                        else:
                            conn.execute(f"ALTER TABLE notes ADD COLUMN {col} INT DEFAULT 0")
                        conn.commit()
                        print(f"Added missing column: {col}")
        
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Database initialization error: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
