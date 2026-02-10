#!/bin/bash

echo "🔍 Checking NotesHub Backend Issues..."

# Check logs
echo "📋 Recent logs:"
sudo journalctl -u noteshub -n 30 --no-pager

echo ""
echo "📁 Checking files in /var/www/noteshub:"
ls -la /var/www/noteshub/

echo ""
echo "🔍 Checking .env file:"
if [ -f /var/www/noteshub/.env ]; then
    echo "✅ .env exists"
else
    echo "❌ .env missing - copying from uploaded location"
    sudo cp /home/ec2-user/.env /var/www/noteshub/.env
fi

echo ""
echo "🐍 Testing Python imports:"
cd /var/www/noteshub
sudo python3.11 -c "import fastapi; print('✅ FastAPI OK')"
sudo python3.11 -c "import sqlalchemy; print('✅ SQLAlchemy OK')"
sudo python3.11 -c "import pymysql; print('✅ PyMySQL OK')"

echo ""
echo "🔧 Testing main.py:"
cd /var/www/noteshub
sudo python3.11 -c "import main; print('✅ main.py imports OK')" 2>&1 | head -20

echo ""
echo "💾 Database connection test:"
mysql -u noteswala -pmahesh -e "SELECT 1;" student_notes_app 2>&1

echo ""
echo "Done! Check errors above."
