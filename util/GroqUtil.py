import os
import httpx
from typing import Dict, Any

class GroqUtil:
    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
    GROQ_MODEL = "groq/compound"
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

    @staticmethod
    async def prompt(system_prompt: Dict[str, Any], user_message: str) -> str:
        headers = {
            "Authorization": f"Bearer {GroqUtil.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": GroqUtil.GROQ_MODEL,
            "messages": [system_prompt, {"role": "user", "content": user_message}],
            "temperature": 1,
            "max_tokens": 1024,
            "top_p": 1
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(GroqUtil.GROQ_API_URL, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPError as e:
            return f"Error contacting Groq API: {str(e)}"
