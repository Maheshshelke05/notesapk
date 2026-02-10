#!/bin/bash

echo "🔧 Fixing NotesHub Backend..."

# 1. Copy .env file
echo "1️⃣ Copying .env file..."
sudo cp /home/ec2-user/.env /var/www/noteshub/.env 2>/dev/null || echo "⚠️ .env not found in home directory"

# 2. Ensure all files are copied
echo "2️⃣ Copying all backend files..."
sudo cp -r /home/ec2-user/*.py /var/www/noteshub/ 2>/dev/null
sudo cp /home/ec2-user/requirements.txt /var/www/noteshub/ 2>/dev/null

# 3. Set permissions
echo "3️⃣ Setting permissions..."
sudo chown -R ec2-user:ec2-user /var/www/noteshub
sudo chmod -R 755 /var/www/noteshub

# 4. Install dependencies again
echo "4️⃣ Installing dependencies..."
cd /var/www/noteshub
sudo python3.11 -m pip install -r requirements.txt --quiet

# 5. Test database connection
echo "5️⃣ Testing database..."
mysql -u noteswala -pmahesh -e "USE student_notes_app; SELECT 'Database OK' as status;" 2>&1

# 6. Test Python import
echo "6️⃣ Testing Python imports..."
cd /var/www/noteshub
sudo python3.11 -c "
try:
    import main
    print('✅ main.py imports successfully')
except Exception as e:
    print(f'❌ Error: {e}')
"

# 7. Restart service
echo "7️⃣ Restarting service..."
sudo systemctl daemon-reload
sudo systemctl restart noteshub

# 8. Check status
echo "8️⃣ Service status:"
sleep 2
sudo systemctl status noteshub --no-pager -l

echo ""
echo "✅ Fix complete! Check status above."
echo "If still failing, run: sudo journalctl -u noteshub -n 50"
