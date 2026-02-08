#!/bin/bash

# AWS EC2 Amazon Linux Setup Script

echo "=== Notes2Cash Backend Deployment ==="

# Update system
sudo yum update -y

# Install Python 3.11
sudo yum install -y python3.11 python3.11-pip

# Install Git
sudo yum install -y git

# Create app directory
sudo mkdir -p /var/www/notes2cash
cd /var/www/notes2cash

# Clone/Copy backend code
# git clone your-repo-url .
# OR upload files manually

# Install dependencies
python3.11 -m pip install -r requirements.txt

# Create systemd service
sudo tee /etc/systemd/system/notes2cash.service > /dev/null <<EOF
[Unit]
Description=Notes2Cash FastAPI Backend
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/var/www/notes2cash
Environment="PATH=/home/ec2-user/.local/bin"
ExecStart=/usr/bin/python3.11 -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start service
sudo systemctl daemon-reload
sudo systemctl start notes2cash
sudo systemctl enable notes2cash

# Install Nginx
sudo yum install -y nginx

# Configure Nginx
sudo tee /etc/nginx/conf.d/notes2cash.conf > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

# Start Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

echo "=== Deployment Complete ==="
echo "API running at: http://YOUR_EC2_IP"
echo "Check status: sudo systemctl status notes2cash"
echo "View logs: sudo journalctl -u notes2cash -f"
