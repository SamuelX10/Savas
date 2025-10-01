import os
import httpx
from typing import Dict, Any, Optional
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

class AssistantUtil:
    BASE_TASKS_URL = "https://tasks.googleapis.com/tasks/v1/lists/@default/tasks"
    BASE_CALENDAR_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    BASE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    # ===== Google API Helpers =====
    @staticmethod
    async def get_google_tasks(access_token: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(AssistantUtil.BASE_TASKS_URL, headers=headers)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            return {"error": str(e)}

    @staticmethod
    async def get_google_calendar(access_token: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(AssistantUtil.BASE_CALENDAR_URL, headers=headers)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            return {"error": str(e)}

    @staticmethod
    async def get_google_user_info(access_token: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(AssistantUtil.BASE_USERINFO_URL, headers=headers)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            return {"error": str(e)}
