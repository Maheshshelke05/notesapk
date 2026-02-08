from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from database import get_db, Note, Transaction
from utils.auth import verify_token
from utils.s3 import upload_to_s3

router = APIRouter(prefix="/api/notes", tags=["notes"])

@router.post("/upload")
async def upload_note(file: UploadFile = File(...), title: str = Form(...), subject: str = Form(...), description: str = Form(...), token: str = Form(...), db: Session = Depends(get_db)):
    user_id = int(verify_token(token))
    file_content = await file.read()
    file_key = f"notes/{user_id}/{datetime.utcnow().timestamp()}_{file.filename}"
    s3_url = upload_to_s3(file_content, file_key)
    note = Note(user_id=user_id, title=title, subject=subject, description=description, price=0, file_path=s3_url)
    db.add(note)
    db.commit()
    db.refresh(note)
    return {"message": "Note uploaded", "note": {"id": note.id, "title": note.title, "url": s3_url}}

@router.get("")
def get_notes(subject: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Note)
    if subject:
        query = query.filter(Note.subject == subject)
    return [{"id": n.id, "title": n.title, "subject": n.subject, "description": n.description, "price": n.price, "downloads": n.downloads, "views": n.views, "shares": n.shares, "likes": n.likes, "user_id": n.user_id, "owner_name": n.owner.name, "file_url": n.file_path} for n in query.all()]

@router.get("/{note_id}")
def get_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"id": note.id, "title": note.title, "subject": note.subject, "description": note.description, "price": note.price}

@router.post("/{note_id}/download")
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

@router.post("/{note_id}/like")
def like_note(note_id: int, token: str, db: Session = Depends(get_db)):
    verify_token(token)
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    note.likes += 1
    db.commit()
    return {"message": "Liked", "likes": note.likes}

@router.post("/{note_id}/share")
def share_note(note_id: int, token: str, db: Session = Depends(get_db)):
    verify_token(token)
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    note.shares += 1
    db.commit()
    return {"message": "Shared", "shares": note.shares}

@router.post("/{note_id}/view")
def view_note(note_id: int, token: str, db: Session = Depends(get_db)):
    verify_token(token)
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    note.views += 1
    db.commit()
    return {"message": "Viewed", "views": note.views}

@router.delete("/{note_id}")
def delete_note(note_id: int, token: str, db: Session = Depends(get_db)):
    user_id = int(verify_token(token))
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == user_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found or unauthorized")
    db.delete(note)
    db.commit()
    return {"message": "Note deleted"}

@router.put("/{note_id}")
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
