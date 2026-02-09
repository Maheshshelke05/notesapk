#!/bin/bash

# Restart backend server
echo "Restarting Notes2Cash API..."

# Stop existing process
sudo systemctl restart notes2cash

# Check status
sudo systemctl status notes2cash

echo "Backend restarted successfully!"
