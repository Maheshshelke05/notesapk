from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
import uvicorn

from database import init_db, get_db, User, LoginLog, Note, NoteLike, NoteDownload, Book, BookImage, BookBuyRequest, Notification, ChatLog, AbuseReport, UserRole, BookStatus, RequestStatus
from auth import create_access_token, create_refresh_token, get_current_user, get_current_admin, blacklist_token, verify_token
from google_auth import google_auth_service
from s3_service import s3_service
from ai_service import ai_service
from utils import rate_limiter, calculate_distance, is_within_radius, reset_daily_counter_if_needed
from config import get_settings
from routes import router
from admin_routes import admin_router
from debug_routes import debug_router

settings = get_settings()
app = FastAPI(title="NotesHub API", version="1.0.0")

app.include_router(router)
app.include_router(admin_router)
app.include_router(debug_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_db()
    print("Database initialized successfully")

@app.get("/")
async def root():
    return {"message": "NotesHub API", "status": "running"}

from pydantic import BaseModel

class GoogleLoginRequest(BaseModel):
    google_token: str
    device_info: str = None

# AUTH ROUTES
@app.post("/api/auth/google")
async def google_login(
    login_data: GoogleLoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    user_info = google_auth_service.verify_google_token(login_data.google_token)
    
    user = db.query(User).filter(User.google_id == user_info['google_id']).first()
    
    if not user:
        user = User(
            email=user_info['email'],
            name=user_info['name'],
            google_id=user_info['google_id'],
            profile_picture=user_info.get('picture'),
            role=UserRole.NORMAL
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="Account is blocked")
    
    ip_address = request.client.host if request else None
    login_log = LoginLog(
        user_id=user.id,
        ip_address=ip_address,
        device_info=login_data.device_info
    )
    db.add(login_log)
    db.commit()
    
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "profile_picture": user.profile_picture
        }
    }

@app.post("/api/auth/refresh")
async def refresh_token_endpoint(refresh_token: str = Form(...), db: Session = Depends(get_db)):
    payload = verify_token(refresh_token, db)
    
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user or user.is_blocked:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    new_access_token = create_access_token({"sub": str(user.id)})
    
    return {"access_token": new_access_token, "token_type": "bearer"}

@app.post("/api/auth/logout")
async def logout(token: str = Form(...), db: Session = Depends(get_db)):
    blacklist_token(token, db)
    return {"message": "Logged out successfully"}

@app.get("/api/user/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "profile_picture": current_user.profile_picture,
        "created_at": current_user.created_at
    }

# NOTES ROUTES
@app.post("/api/notes/upload")
async def upload_note(
    title: str = Form(...),
    subject: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if file.content_type not in ["application/pdf", "application/octet-stream"]:
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > settings.MAX_PDF_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large (max {settings.MAX_PDF_SIZE_MB}MB)")
    
    user_notes_count = db.query(Note).filter(Note.user_id == current_user.id).count()
    max_uploads = 10 if current_user.role == UserRole.PREMIUM else 3
    
    if user_notes_count >= max_uploads:
        raise HTTPException(status_code=400, detail=f"Upload limit reached ({max_uploads} notes)")
    
    file_path = s3_service.upload_note(file_content, file.filename, current_user.id)
    
    note = Note(
        user_id=current_user.id,
        title=title,
        subject=subject,
        description=description,
        file_path=file_path,
        file_size=file_size
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    
    return {"message": "Note uploaded successfully", "note_id": note.id}

@app.get("/api/notes")
async def get_notes(
    skip: int = 0,
    limit: int = 20,
    subject: str = None,
    search: str = None,
    sort: str = "recent",
    db: Session = Depends(get_db)
):
    query = db.query(Note).filter(Note.is_approved == True)
    
    if subject:
        query = query.filter(Note.subject == subject)
    
    if search:
        query = query.filter(
            or_(
                Note.title.ilike(f"%{search}%"),
                Note.description.ilike(f"%{search}%"),
                Note.subject.ilike(f"%{search}%")
            )
        )
    
    if sort == "trending":
        query = query.order_by((Note.downloads + Note.likes * 2 + Note.shares * 3).desc())
    else:
        query = query.order_by(Note.created_at.desc())
    
    notes = query.offset(skip).limit(limit).all()
    
    result = []
    for note in notes:
        result.append({
            "id": note.id,
            "title": note.title,
            "subject": note.subject,
            "description": note.description,
            "downloads": note.downloads,
            "views": note.views,
            "shares": note.shares,
            "likes": note.likes,
            "created_at": note.created_at,
            "user": {
                "id": note.user.id,
                "name": note.user.name
            }
        })
    
    return {"notes": result, "total": query.count()}

@app.get("/api/notes/{note_id}")
async def get_note_detail(note_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    has_liked = db.query(NoteLike).filter(
        NoteLike.note_id == note_id,
        NoteLike.user_id == current_user.id
    ).first() is not None
    
    has_downloaded = db.query(NoteDownload).filter(
        NoteDownload.note_id == note_id,
        NoteDownload.user_id == current_user.id
    ).first() is not None
    
    return {
        "id": note.id,
        "title": note.title,
        "subject": note.subject,
        "description": note.description,
        "downloads": note.downloads,
        "views": note.views,
        "shares": note.shares,
        "likes": note.likes,
        "has_liked": has_liked,
        "has_downloaded": has_downloaded,
        "created_at": note.created_at,
        "user": {
            "id": note.user.id,
            "name": note.user.name
        }
    }

@app.post("/api/notes/{note_id}/download")
async def download_note(
    note_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    ip_address = request.client.host
    
    if not rate_limiter.check_rate_limit(f"download_{ip_address}", 100, 3600):
        raise HTTPException(status_code=429, detail="Too many downloads, try later")
    
    existing_download = db.query(NoteDownload).filter(
        NoteDownload.note_id == note_id,
        NoteDownload.user_id == current_user.id
    ).first()
    
    if not existing_download:
        download = NoteDownload(
            note_id=note_id,
            user_id=current_user.id,
            ip_address=ip_address
        )
        db.add(download)
        note.downloads += 1
        
        # Earnings: 1000 downloads = ₹100, so 1 download = ₹0.1
        note.earnings += 0.1
        
        db.commit()
    
    presigned_url = s3_service.generate_presigned_url(note.file_path, 3600)
    
    return {"download_url": presigned_url, "filename": note.title + ".pdf"}

@app.post("/api/notes/{note_id}/view")
async def track_view(
    note_id: int,
    view_duration: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    note.views += 1
    db.commit()
    
    return {"message": "View tracked"}

@app.post("/api/notes/{note_id}/like")
async def like_note(note_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    existing_like = db.query(NoteLike).filter(
        NoteLike.note_id == note_id,
        NoteLike.user_id == current_user.id
    ).first()
    
    if existing_like:
        db.delete(existing_like)
        note.likes -= 1
        message = "Like removed"
    else:
        like = NoteLike(note_id=note_id, user_id=current_user.id)
        db.add(like)
        note.likes += 1
        message = "Note liked"
    
    db.commit()
    return {"message": message, "likes": note.likes}

@app.post("/api/notes/{note_id}/share")
async def share_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    note.shares += 1
    db.commit()
    
    return {"message": "Share counted"}

@app.delete("/api/notes/{note_id}")
async def delete_note(note_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    if note.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    s3_service.delete_file(note.file_path)
    db.delete(note)
    db.commit()
    
    return {"message": "Note deleted"}

@app.get("/api/user/my-notes")
async def get_my_notes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notes = db.query(Note).filter(Note.user_id == current_user.id).order_by(Note.created_at.desc()).all()
    
    result = []
    for note in notes:
        result.append({
            "id": note.id,
            "title": note.title,
            "subject": note.subject,
            "downloads": note.downloads,
            "views": note.views,
            "shares": note.shares,
            "likes": note.likes,
            "earnings": note.earnings,
            "created_at": note.created_at
        })
    
    return {"notes": result}

@app.get("/api/user/earnings")
async def get_earnings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total_earnings = db.query(func.sum(Note.earnings)).filter(Note.user_id == current_user.id).scalar() or 0
    total_downloads = db.query(func.sum(Note.downloads)).filter(Note.user_id == current_user.id).scalar() or 0
    total_views = db.query(func.sum(Note.views)).filter(Note.user_id == current_user.id).scalar() or 0
    
    return {
        "total_earnings": round(total_earnings, 2),
        "total_downloads": total_downloads,
        "total_views": total_views
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=False)
