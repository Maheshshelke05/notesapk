# Backend - Notes2Cash API

FastAPI backend for Notes2Cash application.

## Features
- JWT Authentication
- Google OAuth integration
- AWS S3 file storage
- MySQL database
- RESTful API endpoints

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Run server:
```bash
python main.py
```

Server runs at: http://localhost:8000
API Docs: http://localhost:8000/docs

## API Endpoints

See main README.md for complete API documentation.

## Deployment

Use `deploy.sh` for AWS EC2 deployment.
