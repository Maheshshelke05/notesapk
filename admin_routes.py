from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db, User, Note, Book, AbuseReport, UserRole
from auth import get_current_admin

admin_router = APIRouter(prefix="/api/admin")

@admin_router.get("/users")
async def get_all_users(
    skip: int = 0,
    limit: int = 50,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    users = db.query(User).offset(skip).limit(limit).all()
    
    result = []
    for user in users:
        result.append({
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "is_blocked": user.is_blocked,
            "created_at": user.created_at
        })
    
    return {"users": result}

@admin_router.post("/users/{user_id}/block")
async def block_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_blocked = True
    db.commit()
    
    return {"message": "User blocked"}

@admin_router.post("/users/{user_id}/unblock")
async def unblock_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_blocked = False
    db.commit()
    
    return {"message": "User unblocked"}

@admin_router.post("/users/{user_id}/promote-premium")
async def promote_to_premium(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.role = UserRole.PREMIUM
    db.commit()
    
    return {"message": "User promoted to premium"}

@admin_router.get("/analytics")
async def get_analytics(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    total_users = db.query(func.count(User.id)).scalar()
    total_notes = db.query(func.count(Note.id)).scalar()
    total_books = db.query(func.count(Book.id)).scalar()
    total_earnings = db.query(func.sum(Note.earnings)).scalar() or 0
    
    return {
        "total_users": total_users,
        "total_notes": total_notes,
        "total_books": total_books,
        "total_earnings": round(total_earnings, 2)
    }

@admin_router.get("/reports")
async def get_abuse_reports(
    skip: int = 0,
    limit: int = 50,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    reports = db.query(AbuseReport).offset(skip).limit(limit).all()
    
    result = []
    for report in reports:
        result.append({
            "id": report.id,
            "reporter_id": report.reporter_id,
            "reported_user_id": report.reported_user_id,
            "content_type": report.content_type,
            "content_id": report.content_id,
            "reason": report.reason,
            "status": report.status,
            "created_at": report.created_at
        })
    
    return {"reports": result}
