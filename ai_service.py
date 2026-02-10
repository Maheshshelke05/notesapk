import httpx
from config import get_settings
from fastapi import HTTPException

settings = get_settings()

class AIService:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile"
    
    async def chat(self, message: str, max_tokens: int = 500) -> dict:
        """Send message to AI and get response"""
        if len(message) > 2000:
            raise HTTPException(status_code=400, detail="Message too long (max 2000 characters)")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful AI assistant for students. Help them with their studies, homework, and learning."},
                {"role": "user", "content": message}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.base_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                return {
                    "response": data["choices"][0]["message"]["content"],
                    "tokens_used": data.get("usage", {}).get("total_tokens", 0)
                }
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

ai_service = AIService()
