from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
import jwt
from datetime import datetime, timedelta
import os
from database import init_db, get_db, User, Note, Transaction

app = FastAPI(title="Notes2Cash API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
UPLOAD_DIR = "uploads/notes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize database tables
init_db()

class UserCreate(BaseModel):
    email: str
    name: str
    google_id: str

class NoteCreate(BaseModel):
    title: str
    subject: str
    description: str
    price: float

class LoginRequest(BaseModel):
    google_token: str

def create_token(user_id: str):
    payload = {"user_id": user_id, "exp": datetime.utcnow() + timedelta(days=30)}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/")
def root():
    return {"message": "Notes2Cash API", "status": "running"}

@app.post("/api/auth/google")
def google_login(request: dict, db: Session = Depends(get_db)):
    email = request.get('email')
    name = request.get('name')
    google_id = request.get('google_id')
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, name=name, google_id=google_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    token = create_token(str(user.id))
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.name}}

@app.get("/api/user/profile")
def get_profile(token: str, db: Session = Depends(get_db)):
    user_id = int(verify_token(token))
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user.id, "email": user.email, "name": user.name}

@app.post("/api/notes/upload")
async def upload_note(title: str, subject: str, description: str, price: float, file: UploadFile = File(...), token: str = None, db: Session = Depends(get_db)):
    user_id = int(verify_token(token))
    file_path = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    note = Note(
        user_id=user_id,
        title=title,
        subject=subject,
        description=description,
        price=price,
        file_path=file_path
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return {"message": "Note uploaded", "note": {"id": note.id, "title": note.title, "price": note.price}}

@app.get("/api/notes")
def get_notes(subject: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Note)
    if subject:
        query = query.filter(Note.subject == subject)
    notes = query.all()
    return [{"id": n.id, "title": n.title, "subject": n.subject, "price": n.price, "downloads": n.downloads} for n in notes]

@app.get("/api/notes/{note_id}")
def get_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"id": note.id, "title": note.title, "subject": note.subject, "description": note.description, "price": note.price}

@app.post("/api/notes/{note_id}/download")
def download_note(note_id: int, token: str, db: Session = Depends(get_db)):
    user_id = int(verify_token(token))
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    note.downloads += 1
    note.earnings += note.price
    
    transaction = Transaction(note_id=note.id, buyer_id=user_id, amount=note.price)
    db.add(transaction)
    db.commit()
    
    return {"message": "Download successful", "file_path": note.file_path}

@app.get("/api/user/earnings")
def get_earnings(token: str, db: Session = Depends(get_db)):
    user_id = int(verify_token(token))
    user_notes = db.query(Note).filter(Note.user_id == user_id).all()
    total_earnings = sum(n.earnings for n in user_notes)
    total_downloads = sum(n.downloads for n in user_notes)
    return {
        "total_earnings": total_earnings,
        "total_downloads": total_downloads,
        "notes_count": len(user_notes)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
