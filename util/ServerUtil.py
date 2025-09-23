import os
import httpx
from typing import Dict, Any

class ServerUtil:
    @staticmethod
    async def get_google_access_token() -> str:
        url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN"),
            "grant_type": "refresh_token"
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=payload)
            resp.raise_for_status()
            return resp.json()["access_token"]

    @staticmethod
    async def get_google_user_info(access_token: str) -> Dict[str, Any]:
        url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()
