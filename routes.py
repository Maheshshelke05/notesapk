from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timedelta
from typing import List

from database import get_db, User, Book, BookImage, BookBuyRequest, Notification, ChatLog, BookStatus, BookCondition, RequestStatus, UserRole
from auth import get_current_user
from s3_service import s3_service
from ai_service import ai_service
from utils import rate_limiter, is_within_radius, reset_daily_counter_if_needed, calculate_distance

router = APIRouter()

# BOOKS ROUTES
@router.post("/api/books/upload")
async def upload_book(
    title: str = Form(...),
    description: str = Form(None),
    condition: str = Form(...),
    price: float = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    location_name: str = Form(None),
    images: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    print(f"📤 Uploading book with {len(images)} images")
    
    if len(images) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 images allowed")
    
    expires_at = datetime.utcnow() + timedelta(days=30)
    
    book = Book(
        user_id=current_user.id,
        title=title,
        description=description,
        condition=BookCondition(condition),
        price=price,
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        status=BookStatus.AVAILABLE,
        expires_at=expires_at
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    
    print(f"✅ Book created with ID: {book.id}")
    
    uploaded_count = 0
    for idx, image in enumerate(images):
        print(f"📷 Processing image {idx + 1}: {image.filename}, type: {image.content_type}")
        
        # Accept octet-stream and check file extension
        valid_types = ["image/jpeg", "image/png", "image/jpg", "application/octet-stream"]
        if image.content_type not in valid_types:
            print(f"❌ Skipped - invalid type: {image.content_type}")
            continue
        
        # Check file extension
        if not image.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            print(f"❌ Skipped - invalid extension: {image.filename}")
            continue
        
        image_content = await image.read()
        print(f"📏 Image size: {len(image_content)} bytes")
        
        if len(image_content) > 5 * 1024 * 1024:
            print(f"❌ Skipped - too large")
            continue
        
        try:
            image_path = s3_service.upload_book_image(image_content, image.filename, current_user.id)
            print(f"☁️ Uploaded to S3: {image_path}")
            
            book_image = BookImage(
                book_id=book.id,
                image_path=image_path,
                is_primary=(idx == 0)
            )
            db.add(book_image)
            uploaded_count += 1
            print(f"✅ Image {idx + 1} saved to database")
        except Exception as e:
            print(f"❌ Error uploading image {idx + 1}: {e}")
    
    db.commit()
    print(f"🎉 Total {uploaded_count} images uploaded for book {book.id}")
    
    return {"message": "Book uploaded successfully", "book_id": book.id, "images_uploaded": uploaded_count}

@router.get("/api/books")
async def get_books(
    skip: int = 0,
    limit: int = 20,
    latitude: float = None,
    longitude: float = None,
    radius: float = 10,
    search: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(Book).filter(
        Book.status == BookStatus.AVAILABLE,
        Book.expires_at > datetime.utcnow()
    )
    
    if search:
        query = query.filter(
            or_(
                Book.title.ilike(f"%{search}%"),
                Book.description.ilike(f"%{search}%")
            )
        )
    
    books = query.order_by(Book.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for book in books:
        distance = None
        if latitude and longitude:
            distance = round(calculate_distance(latitude, longitude, book.latitude, book.longitude), 2)
            if distance > radius:
                continue
        
        primary_image = next((img for img in book.images if img.is_primary), book.images[0] if book.images else None)
        
        image_url = None
        if primary_image:
            try:
                image_url = s3_service.generate_presigned_url(primary_image.image_path, 86400)  # 24 hours
            except Exception as e:
                print(f"Error generating presigned URL for book {book.id}: {e}")
        
        result.append({
            "id": book.id,
            "title": book.title,
            "description": book.description,
            "condition": book.condition,
            "price": book.price,
            "location_name": book.location_name,
            "distance_km": distance,
            "primary_image": image_url,
            "created_at": book.created_at,
            "user": {
                "id": book.user.id,
                "name": book.user.name
            }
        })
    
    return {"books": result}

@router.get("/api/books/{book_id}")
async def get_book_detail(book_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    images = []
    for img in book.images:
        try:
            url = s3_service.generate_presigned_url(img.image_path, 86400)  # 24 hours
            images.append({
                "id": img.id,
                "url": url,
                "is_primary": img.is_primary
            })
            print(f"✅ Image URL generated for book {book_id}: {img.image_path}")
        except Exception as e:
            print(f"❌ Error generating URL for {img.image_path}: {e}")
    
    has_requested = db.query(BookBuyRequest).filter(
        BookBuyRequest.book_id == book_id,
        BookBuyRequest.buyer_id == current_user.id
    ).first() is not None
    
    print(f"📊 Book {book_id} has {len(images)} images")
    
    return {
        "id": book.id,
        "title": book.title,
        "description": book.description,
        "condition": book.condition,
        "price": book.price,
        "latitude": book.latitude,
        "longitude": book.longitude,
        "location_name": book.location_name,
        "status": book.status,
        "images": images,
        "has_requested": has_requested,
        "is_owner": book.user_id == current_user.id,
        "expires_at": book.expires_at,
        "created_at": book.created_at,
        "user": {
            "id": book.user.id,
            "name": book.user.name
        }
    }

from pydantic import BaseModel
from typing import Optional

class BuyRequestData(BaseModel):
    full_name: str
    mobile_number: str
    latitude: float
    longitude: float
    location_name: Optional[str] = None
    message: Optional[str] = None

@router.post("/api/books/{book_id}/buy-request")
async def create_buy_request(
    book_id: int,
    data: BuyRequestData,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if book.status != BookStatus.AVAILABLE:
        raise HTTPException(status_code=400, detail="Book not available")
    
    if book.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot buy your own book")
    
    ip_address = request.client.host if request else None
    if not rate_limiter.check_rate_limit(f"buy_request_{current_user.id}", 5, 86400):
        raise HTTPException(status_code=429, detail="Maximum 5 buy requests per day")
    
    existing_request = db.query(BookBuyRequest).filter(
        BookBuyRequest.book_id == book_id,
        BookBuyRequest.buyer_id == current_user.id
    ).first()
    
    if existing_request:
        raise HTTPException(status_code=400, detail="Already requested this book")
    
    buy_request = BookBuyRequest(
        book_id=book_id,
        buyer_id=current_user.id,
        full_name=data.full_name,
        mobile_number=data.mobile_number,
        latitude=data.latitude,
        longitude=data.longitude,
        location_name=data.location_name,
        message=data.message,
        status=RequestStatus.PENDING
    )
    db.add(buy_request)
    db.flush()
    
    notification = Notification(
        user_id=book.user_id,
        title="New Buy Request",
        message=f"{current_user.name} wants to buy your book: {book.title}"
    )
    db.add(notification)
    
    db.commit()
    
    print(f"✅ Notification created for user {book.user_id}: {current_user.name} wants to buy {book.title}")
    
    return {"message": "Buy request sent successfully"}

@router.get("/api/user/my-books")
async def get_my_books(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    books = db.query(Book).filter(Book.user_id == current_user.id).order_by(Book.created_at.desc()).all()
    
    result = []
    for book in books:
        primary_image = next((img for img in book.images if img.is_primary), book.images[0] if book.images else None)
        
        pending_requests = db.query(BookBuyRequest).filter(
            BookBuyRequest.book_id == book.id,
            BookBuyRequest.status == RequestStatus.PENDING
        ).count()
        
        image_url = None
        if primary_image:
            try:
                image_url = s3_service.generate_presigned_url(primary_image.image_path, 86400)  # 24 hours
            except Exception as e:
                print(f"Error generating presigned URL: {e}")
        
        result.append({
            "id": book.id,
            "title": book.title,
            "price": book.price,
            "status": book.status,
            "primary_image": image_url,
            "requests_count": pending_requests,
            "created_at": book.created_at,
            "expires_at": book.expires_at
        })
    
    return {"books": result}

@router.get("/api/books/{book_id}/requests")
async def get_book_requests(book_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if book.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    requests = db.query(BookBuyRequest).filter(BookBuyRequest.book_id == book_id).order_by(BookBuyRequest.created_at.desc()).all()
    
    result = []
    for req in requests:
        result.append({
            "id": req.id,
            "buyer": {
                "id": req.buyer.id,
                "name": req.buyer.name
            },
            "full_name": req.full_name,
            "mobile_number": req.mobile_number,
            "location_name": req.location_name,
            "message": req.message,
            "status": req.status,
            "created_at": req.created_at
        })
    
    return {"requests": result}

@router.post("/api/books/requests/{request_id}/accept")
async def accept_request(request_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    buy_request = db.query(BookBuyRequest).filter(BookBuyRequest.id == request_id).first()
    if not buy_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    book = buy_request.book
    if book.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    buy_request.status = RequestStatus.ACCEPTED
    book.status = BookStatus.RESERVED
    
    notification = Notification(
        user_id=buy_request.buyer_id,
        title="Request Accepted",
        message=f"Your request for {book.title} has been accepted"
    )
    db.add(notification)
    
    db.commit()
    
    return {"message": "Request accepted"}

@router.post("/api/books/requests/{request_id}/reject")
async def reject_request(request_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    buy_request = db.query(BookBuyRequest).filter(BookBuyRequest.id == request_id).first()
    if not buy_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    book = buy_request.book
    if book.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    buy_request.status = RequestStatus.REJECTED
    
    notification = Notification(
        user_id=buy_request.buyer_id,
        title="Request Rejected",
        message=f"Your request for {book.title} has been rejected"
    )
    db.add(notification)
    
    db.commit()
    
    return {"message": "Request rejected"}

@router.post("/api/books/{book_id}/mark-sold")
async def mark_book_sold(book_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if book.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    book.status = BookStatus.SOLD
    db.commit()
    
    return {"message": "Book marked as sold"}

@router.delete("/api/books/{book_id}")
async def delete_book(book_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if book.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    for image in book.images:
        s3_service.delete_file(image.image_path)
    
    db.delete(book)
    db.commit()
    
    return {"message": "Book deleted"}

# AI CHAT ROUTES
@router.post("/api/ai/chat")
async def ai_chat(
    message: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reset_daily_counter_if_needed(current_user, "ai_messages_today", "ai_messages_reset_date")
    
    max_messages = 100 if current_user.role == UserRole.PREMIUM else 50
    
    if current_user.ai_messages_today >= max_messages:
        raise HTTPException(status_code=429, detail=f"Daily limit reached ({max_messages} messages)")
    
    ai_response = await ai_service.chat(message)
    
    chat_log = ChatLog(
        user_id=current_user.id,
        message=message,
        response=ai_response["response"],
        tokens_used=ai_response["tokens_used"]
    )
    db.add(chat_log)
    
    current_user.ai_messages_today += 1
    db.commit()
    
    return {
        "response": ai_response["response"],
        "messages_remaining": max_messages - current_user.ai_messages_today
    }

@router.get("/api/ai/chat-history")
async def get_chat_history(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chats = db.query(ChatLog).filter(
        ChatLog.user_id == current_user.id
    ).order_by(ChatLog.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for chat in chats:
        result.append({
            "id": chat.id,
            "message": chat.message,
            "response": chat.response,
            "created_at": chat.created_at
        })
    
    return {"chats": result}

# NOTIFICATIONS
@router.get("/api/notifications")
async def get_notifications(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for notif in notifications:
        result.append({
            "id": notif.id,
            "title": notif.title,
            "message": notif.message,
            "is_read": notif.is_read,
            "created_at": notif.created_at
        })
    
    return {"notifications": result}

@router.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db.commit()
    
    return {"message": "Notification marked as read"}
