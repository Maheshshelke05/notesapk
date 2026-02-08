from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, User
from utils.auth import create_token, verify_token

router = APIRouter(tags=["auth"])

@router.post("/api/auth/google")
def google_login(request: dict, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.get('email')).first()
    if not user:
        user = User(email=request.get('email'), name=request.get('name'), google_id=request.get('google_id'))
        db.add(user)
        db.commit()
        db.refresh(user)
    return {"token": create_token(str(user.id)), "user": {"id": user.id, "email": user.email, "name": user.name}}

@router.get("/api/user/profile")
def get_profile(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == int(verify_token(token))).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user.id, "email": user.email, "name": user.name}

@router.get("/api/user/my-notes")
def get_my_notes(token: str, db: Session = Depends(get_db)):
    user_id = int(verify_token(token))
    from database import Note
    notes = db.query(Note).filter(Note.user_id == user_id).all()
    return [{"id": n.id, "title": n.title, "subject": n.subject, "downloads": n.downloads, "views": n.views, "shares": n.shares, "likes": n.likes, "earnings": n.earnings} for n in notes]

@router.get("/api/user/earnings")
def get_earnings(token: str, db: Session = Depends(get_db)):
    user_id = int(verify_token(token))
    from database import Note
    user_notes = db.query(Note).filter(Note.user_id == user_id).all()
    return {"total_earnings": sum(n.earnings for n in user_notes), "total_downloads": sum(n.downloads for n in user_notes), "notes_count": len(user_notes)}

@router.post("/api/user/upgrade-premium")
def upgrade_premium(token: str, db: Session = Depends(get_db)):
    user_id = int(verify_token(token))
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_premium = 1
    db.commit()
    return {"message": "Upgraded to premium", "is_premium": True}
