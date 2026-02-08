from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from database import init_db
from routes import auth, notes
from config.settings import UPLOAD_DIR

app = FastAPI(title="Notes2Cash API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(UPLOAD_DIR, exist_ok=True)
init_db()

@app.get("/")
def root():
    return {"message": "Notes2Cash API", "status": "running"}

app.include_router(auth.router)
app.include_router(notes.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
