#!/bin/bash

echo "Testing backend setup..."

cd /home/ec2-user

echo "1. Checking if files exist:"
ls -la *.py

echo -e "\n2. Testing Python imports:"
python3 -c "from auth_routes import router; print('auth_routes OK')" 2>&1
python3 -c "from notes_routes import router; print('notes_routes OK')" 2>&1
python3 -c "from main import app; print('main.py OK')" 2>&1

echo -e "\n3. Checking routes:"
python3 -c "from main import app; print([r.path for r in app.routes])" 2>&1

echo -e "\n4. Testing API:"
curl -s http://localhost:8000/ | head -20
curl -s "http://localhost:8000/api/user/earnings?token=test" | head -20
