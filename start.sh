#!/bin/bash

echo "🚀 Starting NotesHub Backend..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Copy .env.example to .env and configure it first"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found!"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Check MariaDB/MySQL
echo "🔍 Checking database connection..."
mysql -u noteswala -pmahesh -e "USE student_notes_app;" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Database not accessible. Creating database..."
    mysql -u root -e "CREATE DATABASE IF NOT EXISTS student_notes_app;"
    mysql -u root -e "CREATE USER IF NOT EXISTS 'noteswala'@'localhost' IDENTIFIED BY 'mahesh';"
    mysql -u root -e "GRANT ALL PRIVILEGES ON student_notes_app.* TO 'noteswala'@'localhost';"
    mysql -u root -e "FLUSH PRIVILEGES;"
fi

# Start server
echo "✅ Starting FastAPI server..."
echo "📍 Server will run at http://localhost:8000"
echo "📚 API docs at http://localhost:8000/docs"
echo ""
python main.py
