#!/bin/bash

echo "Starting NotesHub Backend Deployment..."

# Update system
sudo yum update -y

# Install Python 3.11
sudo yum install python3.11 python3.11-pip -y

# Install MariaDB
sudo yum install mariadb105-server -y
sudo systemctl start mariadb
sudo systemctl enable mariadb

# Secure MariaDB installation
sudo mysql -e "CREATE DATABASE IF NOT EXISTS student_notes_app;"
sudo mysql -e "CREATE USER IF NOT EXISTS 'noteswala'@'localhost' IDENTIFIED BY 'SecurePassword123!';"
sudo mysql -e "GRANT ALL PRIVILEGES ON student_notes_app.* TO 'noteswala'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"

# Install Nginx
sudo yum install nginx -y

# Create application directory
sudo mkdir -p /var/www/noteshub
sudo cp -r * /var/www/noteshub/
cd /var/www/noteshub

# Install Python dependencies
python3.11 -m pip install --upgrade pip
python3.11 -m pip install -r requirements.txt

# Create .env file (user must edit this)
if [ ! -f .env ]; then
    cp .env.example .env
    echo "IMPORTANT: Edit /var/www/noteshub/.env with your credentials"
fi

# Create systemd service
sudo tee /etc/systemd/system/noteshub.service > /dev/null <<EOF
[Unit]
Description=NotesHub FastAPI Application
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/var/www/noteshub
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/python3.11 -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Configure Nginx
sudo tee /etc/nginx/conf.d/noteshub.conf > /dev/null <<EOF
server {
    listen 80;
    server_name _;
    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Start services
sudo systemctl daemon-reload
sudo systemctl start noteshub
sudo systemctl enable noteshub
sudo systemctl restart nginx
sudo systemctl enable nginx

echo "Deployment complete!"
echo "Edit /var/www/noteshub/.env with your credentials"
echo "Then restart: sudo systemctl restart noteshub"
