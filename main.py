from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from database import init_db
from auth_routes import router as auth_router
from notes_routes import router as notes_router

app = FastAPI(title="Notes2Cash API")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

UPLOAD_DIR = "uploads/notes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

init_db()

@app.get("/")
def root():
    return {"message": "Notes2Cash API", "status": "running"}

app.include_router(auth_router)
app.include_router(notes_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
