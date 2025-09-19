import os
import json
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import asyncio
import websockets
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

# ================== GLOBAL VARIABLES ==================
scheduler = None
connected_clients = set()
pending_messages = []
routine_pairs = []
assistant_tools = {}

# ================== ASSISTANT TOOLS ==================
async def fetch_music():
    await broadcast("🎵 Time for music!")

async def fetch_news():
    news_api_key = os.environ.get("NEWS_API_KEY")
    if not news_api_key:
        msg = "NEWS_API_KEY not declared!"
        await broadcast(msg, store_if_offline=True)
        return

    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "country": "ng",   
        "pageSize": 3,
        "apiKey": news_api_key
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            articles = response.json().get("articles", [])

        if not articles:
            msg = "No news found today."
        else:
            headlines = [f"- {a['title']}" for a in articles[:3]]
            msg = "Morning News:\n" + "\n".join(headlines)
    except Exception as e:
        msg = f"News fetch error: {str(e)}"
    
    await broadcast(msg, store_if_offline=True)

# ================== GROQ VARIABLES ==================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "groq/compound"

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

groq_respond = lambda msg: asyncio.to_thread(
    lambda: httpx.post(
        GROQ_API_URL,
        headers=headers,
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": msg}],
            "temperature": 1,
            "max_tokens": 1024,
            "top_p": 1,
        },
        timeout=30
    )
)

# ================== MAIN ==================
async def main():
    initialize_variables()
    initialize_logic()
    await start_server()

# ================== INITIALIZATION ==================
def initialize_variables():
    global scheduler, routine_pairs, assistant_tools
    scheduler = AsyncIOScheduler()

    assistant_tools = {
        "news": fetch_news,
        "music": fetch_music,
        "reminder": lambda msg: scheduled_task(msg)
    }

    routine_pairs = [
        ("05:00", "news"),
        ("13:00", "reminder", "Lunch Reminder"),
        ("20:00", "reminder", "Night Reflection"),
        ("15:00", "music")
    ]

def initialize_logic():
    scheduler.start()
    scheduler.add_job(call_self, "interval", minutes=13)
    
    for routine in routine_pairs:
        hour, minute = map(int, routine[0].split(":"))
        tool_key = routine[1]
        tool_func = assistant_tools.get(tool_key)
        if not tool_func:
            continue
        if len(routine) > 2:
            scheduler.add_job(tool_func, "cron", hour=hour, minute=minute, args=[routine[2]])
        else:
            scheduler.add_job(tool_func, "cron", hour=hour, minute=minute)

async def start_server():
    PORT = int(os.environ.get("PORT", 10000))
    async with websockets.serve(handler, "0.0.0.0", PORT):
        await asyncio.Future()

# ================== HELPER METHODS ==================
async def broadcast(message: str, store_if_offline=False):
    if connected_clients:
        for ws in connected_clients.copy():
            try:
                await ws.send(message)
            except:
                connected_clients.discard(ws)
    elif store_if_offline:
        pending_messages.append(message)

async def call_self():
    web_socket_url = os.environ.get("WEB_SOCKET_URL", "ws://localhost:10000")
    try:
        async with websockets.connect(web_socket_url) as websocket:
            await websocket.send("ping")
            await websocket.recv()
    except Exception as e:
        print(f"call_self error: {e}")

async def scheduled_task(message: str):
    await broadcast(f"⏰ Reminder: {message}")


import json

async def process_message(message: str) -> str:
    # Try parse as JSON
    try:
        data = json.loads(message)
        msg_type = data.get("type")

        if msg_type == "login" and data.get("provider") == "google":
            return "🔑 Google login requested, send me the token."

        if msg_type == "token" and data.get("provider") == "google":
            token = data.get("token")
            return f"✅ Google token received: {token[:10]}..."  # preview first 10 chars

        return "⚠️ Unknown JSON message type."

    except json.JSONDecodeError:
        # Not JSON → normal chat
        try:
            response = await groq_respond(message)
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"Groq error: {str(e)}"


# ================== WEBSOCKET HANDLER ==================
async def handler(websocket):
    connected_clients.add(websocket)
    if pending_messages:
        for msg in pending_messages:
            await websocket.send(f"(📬 Missed) {msg}")
        pending_messages.clear()
    try:
        async for message in websocket:
            reply = await process_message(message)
            await websocket.send(reply)
    finally:
        connected_clients.discard(websocket)



load_dotenv()

app = Flask(__name__)

# Google OAuth settings
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "postmessage")

TOKENS = {}  # Simple in-memory store {user_id: {access, refresh, expiry}}

@app.route("/auth/google", methods=["POST"])
def google_auth():
    data = request.json
    server_auth_code = data.get("code")

    if not server_auth_code:
        return jsonify({"error": "Missing serverAuthCode"}), 400

    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "code": server_auth_code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    try:
        res = requests.post(token_url, data=payload)
        res.raise_for_status()
        token_data = res.json()

        # For demo, just return the tokens
        return jsonify(token_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    asyncio.run(main())
