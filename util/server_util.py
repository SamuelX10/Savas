async def get_google_access_token():
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

