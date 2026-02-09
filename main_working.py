from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
import jwt
from datetime import datetime, timedelta
import os
import boto3
from database import init_db, get_db, User, Note, Transaction

app = FastAPI(title="Notes2Cash API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
UPLOAD_DIR = "uploads/notes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_BUCKET = os.getenv("AWS_S3_BUCKET", "noteshub-free-wala")
s3_client = boto3.client('s3', region_name=AWS_REGION, aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"), aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"))

init_db()

# ============ AUTH UTILS ============
def create_token(user_id: str):
    return jwt.encode({"user_id": user_id, "exp": datetime.utcnow() + timedelta(days=30)}, SECRET_KEY, algorithm="HS256")

def verify_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])["user_id"]
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

# ============ ROOT ============
@app.get("/")
def root():
    return {"message": "Notes2Cash API", "status": "running"}

# ============ AUTH ROUTES ============
@app.post("/api/auth/google")
def google_login(request: dict, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.get('email')).first()
    if not user:
        user = User(email=request.get('email'), name=request.get('name'), google_id=request.get('google_id'))
        db.add(user)
        db.commit()
        db.refresh(user)
    return {"token": create_token(str(user.id)), "user": {"id": user.id, "email": user.email, "name": user.name}}

@app.get("/api/user/profile")
def get_profile(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == int(verify_token(token))).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user.id, "email": user.email, "name": user.name}

@app.get("/api/user/my-notes")
def get_my_notes(token: str, db: Session = Depends(get_db)):
    user_id = int(verify_token(token))
    notes = db.query(Note).filter(Note.user_id == user_id).all()
    return [{"id": n.id, "title": n.title, "subject": n.subject, "downloads": n.downloads, "views": n.views, "shares": n.shares, "likes": n.likes, "earnings": n.earnings} for n in notes]

@app.get("/api/user/earnings")
def get_earnings(token: str, db: Session = Depends(get_db)):
    user_id = int(verify_token(token))
    user_notes = db.query(Note).filter(Note.user_id == user_id).all()
    return {"total_earnings": sum(n.earnings for n in user_notes), "total_downloads": sum(n.downloads for n in user_notes), "notes_count": len(user_notes)}

@app.post("/api/user/upgrade-premium")
def upgrade_premium(token: str, db: Session = Depends(get_db)):
    user_id = int(verify_token(token))
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_premium = 1
    db.commit()
    return {"message": "Upgraded to premium", "is_premium": True}

# ============ NOTES ROUTES ============
@app.post("/api/notes/upload")
async def upload_note(file: UploadFile = File(...), title: str = Form(...), subject: str = Form(...), description: str = Form(...), token: str = Form(...), db: Session = Depends(get_db)):
    user_id = int(verify_token(token))
    file_content = await file.read()
    file_key = f"notes/{user_id}/{datetime.utcnow().timestamp()}_{file.filename}"
    s3_client.put_object(Bucket=AWS_BUCKET, Key=file_key, Body=file_content, ContentType='application/pdf', ACL='public-read')
    s3_url = f"https://{AWS_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{file_key}"
    note = Note(user_id=user_id, title=title, subject=subject, description=description, price=0, file_path=s3_url)
    db.add(note)
    db.commit()
    db.refresh(note)
    return {"message": "Note uploaded", "note": {"id": note.id, "title": note.title, "url": s3_url}}

@app.get("/api/notes")
def get_notes(subject: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Note)
    if subject:
        query = query.filter(Note.subject == subject)
    return [{"id": n.id, "title": n.title, "subject": n.subject, "description": n.description, "price": n.price, "downloads": n.downloads, "views": n.views, "shares": n.shares, "likes": n.likes, "user_id": n.user_id, "owner_name": n.owner.name, "file_url": n.file_path} for n in query.all()]

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
    db.add(Transaction(note_id=note.id, buyer_id=user_id, amount=note.price))
    db.commit()
    return {"message": "Download successful", "file_url": note.file_path}

@app.post("/api/notes/{note_id}/like")
def like_note(note_id: int, token: str, db: Session = Depends(get_db)):
    verify_token(token)
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    note.likes += 1
    db.commit()
    return {"message": "Liked", "likes": note.likes}

@app.post("/api/notes/{note_id}/share")
def share_note(note_id: int, token: str, db: Session = Depends(get_db)):
    verify_token(token)
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    note.shares += 1
    db.commit()
    return {"message": "Shared", "shares": note.shares}

@app.post("/api/notes/{note_id}/view")
def view_note(note_id: int, token: str, db: Session = Depends(get_db)):
    verify_token(token)
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    note.views += 1
    db.commit()
    return {"message": "Viewed", "views": note.views}

@app.delete("/api/notes/{note_id}")
def delete_note(note_id: int, token: str, db: Session = Depends(get_db)):
    user_id = int(verify_token(token))
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == user_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found or unauthorized")
    db.delete(note)
    db.commit()
    return {"message": "Note deleted"}

@app.put("/api/notes/{note_id}")
def update_note(note_id: int, title: str, subject: str, description: str, price: float, token: str, db: Session = Depends(get_db)):
    user_id = int(verify_token(token))
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == user_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found or unauthorized")
    note.title = title
    note.subject = subject
    note.description = description
    note.price = price
    db.commit()
    return {"message": "Note updated", "note": {"id": note.id, "title": note.title}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
