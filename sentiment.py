from fastapi import APIRouter
import requests
import os

router = APIRouter()

@router.get("/chat/{message}")
async def chat(message: str):
    """Send the message to Hugging Face and return a generated response."""
    try:
        api_key = os.getenv("HUGGINGFACE_API_KEY")

        inference_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        prompt = f"{message}\n\nPlease respond in 1-2 short lines."
        data = {
            "inputs": prompt,
        }

        response = requests.post(inference_url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        generated_text = result[0]["generated_text"]
        cleaned_text = generated_text[len(prompt):].strip()

        return {"response": cleaned_text}

    except Exception as e:
        return {"error": str(e)}
