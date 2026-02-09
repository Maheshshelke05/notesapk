#!/bin/bash

echo "Starting Notes2Cash API Deployment..."

# Update system
sudo yum update -y

# Install Python 3.11
sudo yum install python3.11 python3.11-pip -y

# Install MySQL
sudo yum install mysql -y

# Install dependencies
pip3.11 install -r requirements.txt

# Create systemd service
sudo tee /etc/systemd/system/notes2cash.service > /dev/null <<EOF
[Unit]
Description=Notes2Cash API
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user
ExecStart=/usr/bin/python3.11 -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable notes2cash
sudo systemctl start notes2cash

echo "Deployment complete!"
echo "Check status: sudo systemctl status notes2cash"
echo "View logs: sudo journalctl -u notes2cash -f"
