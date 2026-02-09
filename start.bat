@echo off
echo Starting NotesHub Backend...

if not exist .env (
    echo .env file not found!
    echo Copy .env.example to .env and configure it first
    pause
    exit /b 1
)

echo Installing dependencies...
pip install -r requirements.txt

echo Starting FastAPI server...
echo Server will run at http://localhost:8000
echo API docs at http://localhost:8000/docs
echo.
python main.py
pause
