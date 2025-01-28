from fastapi import APIRouter
import requests
import os

router = APIRouter()

@router.get("/chat/{message}")
async def chat(message: str):
    """Send the message to OpenRouter and return a generated response."""
    try:
        api_key = os.getenv("OPENROUTER_API_KEY")  
        site_url = os.getenv("YOUR_SITE_URL")  
        site_name = os.getenv("YOUR_SITE_NAME")  
        
        inference_url = "https://openrouter.ai/api/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": site_url,
            "X-Title": site_name,
        }
        
      
        prompt = message
        data = {
            "model": "google/gemini-2.0-flash-thinking-exp:free",  
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
        }

        response = requests.post(inference_url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        generated_text = result.get('choices', [{}])[0].get('message', {}).get('content', 'No content returned')
        
        return {"response": generated_text.strip()}

    except Exception as e:
        return {"error": str(e)}
