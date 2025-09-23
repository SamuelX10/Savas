import os
import httpx
from typing import Dict, Any

class ServerUtil:
    def __init__(self):
        self.base_tasks_url = "https://tasks.googleapis.com/tasks/v1/lists/@default/tasks"
        self.base_calendar_url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        self.base_userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"

    async def get_google_tasks(self, access_token: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.base_tasks_url, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def get_google_calendar(self, access_token: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.base_calendar_url, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def get_google_user_info(self, access_token: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.base_userinfo_url, headers=headers)
            resp.raise_for_status()
            return resp.json()
