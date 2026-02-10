from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db, Book, BookImage
from auth import get_current_user, User

debug_router = APIRouter()

@debug_router.get("/api/debug/books/{book_id}")
async def debug_book(book_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return {"error": "Book not found"}
    
    images = db.query(BookImage).filter(BookImage.book_id == book_id).all()
    
    return {
        "book_id": book.id,
        "title": book.title,
        "images_count": len(images),
        "images": [
            {
                "id": img.id,
                "image_path": img.image_path,
                "is_primary": img.is_primary
            } for img in images
        ]
    }
