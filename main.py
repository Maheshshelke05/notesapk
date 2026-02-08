from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import jwt
from datetime import datetime, timedelta
import os

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

class User(BaseModel):
    email: str
    name: str
    google_id: str

class Note(BaseModel):
    title: str
    subject: str
    description: str
    price: float

class LoginRequest(BaseModel):
    google_token: str

users_db = {}
notes_db = []

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
def google_login(request: LoginRequest):
    user_id = f"user_{len(users_db) + 1}"
    user = {"id": user_id, "email": "user@example.com", "name": "Test User"}
    users_db[user_id] = user
    token = create_token(user_id)
    return {"token": token, "user": user}

@app.get("/api/user/profile")
def get_profile(token: str):
    user_id = verify_token(token)
    user = users_db.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/api/notes/upload")
async def upload_note(title: str, subject: str, description: str, price: float, file: UploadFile = File(...), token: str = None):
    user_id = verify_token(token)
    file_path = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    note = {
        "id": len(notes_db) + 1,
        "user_id": user_id,
        "title": title,
        "subject": subject,
        "description": description,
        "price": price,
        "file_path": file_path,
        "downloads": 0,
        "earnings": 0,
        "created_at": datetime.utcnow().isoformat()
    }
    notes_db.append(note)
    return {"message": "Note uploaded", "note": note}

@app.get("/api/notes")
def get_notes(subject: Optional[str] = None):
    if subject:
        return [n for n in notes_db if n["subject"] == subject]
    return notes_db

@app.get("/api/notes/{note_id}")
def get_note(note_id: int):
    note = next((n for n in notes_db if n["id"] == note_id), None)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@app.post("/api/notes/{note_id}/download")
def download_note(note_id: int, token: str):
    user_id = verify_token(token)
    note = next((n for n in notes_db if n["id"] == note_id), None)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    note["downloads"] += 1
    note["earnings"] += note["price"]
    return {"message": "Download successful", "file_path": note["file_path"]}

@app.get("/api/user/earnings")
def get_earnings(token: str):
    user_id = verify_token(token)
    user_notes = [n for n in notes_db if n["user_id"] == user_id]
    total_earnings = sum(n["earnings"] for n in user_notes)
    return {
        "total_earnings": total_earnings,
        "total_downloads": sum(n["downloads"] for n in user_notes),
        "notes_count": len(user_notes)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
