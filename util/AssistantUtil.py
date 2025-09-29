import os
import httpx
from typing import Dict, Any, Optional
import gspread
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

    # ===== Google Sheets Memory Helpers =====
    @staticmethod
    def _connect_sheet(sheet_name: str = "AI_Brain", tab_name: str = "Memory"):
        """Connect to Google Sheet and return worksheet."""
        scope = ["https://spreadsheets.google.com/feeds",
                 "https://www.googleapis.com/auth/spreadsheets",
                 "https://www.googleapis.com/auth/drive.file",
                 "https://www.googleapis.com/auth/drive"]
        creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)
        sheet = client.open(sheet_name)
        worksheet = sheet.worksheet(tab_name)
        return worksheet

    @staticmethod
    def remember(key: str, value: str):
        """Add or update a fact in the Memory sheet."""
        worksheet = AssistantUtil._connect_sheet()
        key = key.strip().lower()
        value = value.strip()
        timestamp = datetime.utcnow().isoformat()

        try:
            cell = worksheet.find(key)
            # Update existing row
            worksheet.update_cell(cell.row, 2, value)
            worksheet.update_cell(cell.row, 3, timestamp)
        except gspread.exceptions.CellNotFound:
            # Append new row
            worksheet.append_row([key, value, timestamp])

    @staticmethod
    def recall(key: str) -> Optional[str]:
        """Retrieve a fact by key from the Memory sheet."""
        worksheet = AssistantUtil._connect_sheet()
        key = key.strip().lower()
        try:
            cell = worksheet.find(key)
            return worksheet.cell(cell.row, 2).value
        except gspread.exceptions.CellNotFound:
            return None

    @staticmethod
    def forget(key: str):
        """Remove a fact from the Memory sheet."""
        worksheet = AssistantUtil._connect_sheet()
        key = key.strip().lower()
        try:
            cell = worksheet.find(key)
            worksheet.delete_row(cell.row)
        except gspread.exceptions.CellNotFound:
            pass
