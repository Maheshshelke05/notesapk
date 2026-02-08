import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException
import os

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

def create_token(user_id: str):
    return jwt.encode({"user_id": user_id, "exp": datetime.utcnow() + timedelta(days=30)}, SECRET_KEY, algorithm="HS256")

def verify_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])["user_id"]
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
