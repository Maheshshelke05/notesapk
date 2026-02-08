# Notes2Cash Backend - Python FastAPI

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python main.py

# API will run at: http://localhost:8000
# Docs at: http://localhost:8000/docs
```

## AWS EC2 Deployment

### 1. Launch EC2 Instance
- AMI: Amazon Linux 2023
- Instance Type: t2.micro (free tier)
- Security Group: Allow ports 22, 80, 8000

### 2. Connect to Server
```bash
ssh -i "your-key.pem" ec2-user@YOUR_EC2_IP
```

### 3. Upload Backend Files
```bash
# On your local machine
scp -i "your-key.pem" -r backend/* ec2-user@YOUR_EC2_IP:/home/ec2-user/
```

### 4. Run Deployment Script
```bash
# On EC2 server
cd /home/ec2-user
chmod +x deploy.sh
sudo ./deploy.sh
```

### 5. Verify Deployment
```bash
# Check service status
sudo systemctl status notes2cash

# View logs
sudo journalctl -u notes2cash -f

# Test API
curl http://localhost:8000
```

## API Endpoints

### Auth
- `POST /api/auth/google` - Google login
- `GET /api/user/profile?token=xxx` - Get user profile

### Notes
- `GET /api/notes` - Get all notes
- `GET /api/notes/{id}` - Get note by ID
- `POST /api/notes/upload` - Upload note (requires token)
- `POST /api/notes/{id}/download` - Download note (requires token)

### Earnings
- `GET /api/user/earnings?token=xxx` - Get user earnings

## Environment Variables

Create `.env` file:
```
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///./notes.db
PORT=8000
```

## Flutter Integration

Update API URL in Flutter app:
```dart
class ApiService {
  static const String baseUrl = 'http://YOUR_EC2_IP:8000/api';
}
```
