import os
import json
import asyncio
from datetime import datetime
from aiohttp import web, WSMsgType
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx
from dotenv import load_dotenv

load_dotenv()

# ================== GLOBAL VARIABLES ==================
scheduler = None
connected_clients = set()
pending_messages = []
routine_pairs = []
assistant_tools = {}

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
        "reminder": scheduled_task
    }

    routine_pairs = [
        ("05:00", "news"),
        ("13:00", "reminder", "Lunch Reminder"),
        ("20:00", "reminder", "Night Reflection"),
        ("15:00", "music")
    ]

def initialize_logic():
    scheduler.start()
    # call_self equivalent
    scheduler.add_job(lambda: asyncio.create_task(call_self()), "interval", minutes=13)

    for routine in routine_pairs:
        hour, minute = map(int, routine[0].split(":"))
        tool_key = routine[1]
        tool_func = assistant_tools.get(tool_key)
        if not tool_func:
            continue
        if len(routine) > 2:
            scheduler.add_job(lambda msg=routine[2]: asyncio.create_task(tool_func(msg)), "cron", hour=hour, minute=minute)
        else:
            scheduler.add_job(lambda f=tool_func: asyncio.create_task(f()), "cron", hour=hour, minute=minute)

async def start_server():
PORT = int(os.environ.get("PORT", 10000))
async with websockets.serve(handler, "0.0.0.0", PORT):
await asyncio.Future()


# ================== ASSISTANT TOOLS ==================
async def fetch_music():
    await broadcast("🎵 Time for music!")

async def fetch_news():
    news_api_key = os.environ.get("NEWS_API_KEY")
    if not news_api_key:
        await broadcast("NEWS_API_KEY not declared!", store_if_offline=True)
        return

    url = "https://newsapi.org/v2/top-headlines"
    params = {"country": "ng", "pageSize": 3, "apiKey": news_api_key}
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

async def scheduled_task(message: str):
    await broadcast(f"⏰ Reminder: {message}")

# ================== GROQ VARIABLES ==================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "groq/compound"

async def groq_respond(msg: str):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            GROQ_API_URL,
            headers=headers,
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": msg}],
                "temperature": 1,
                "max_tokens": 1024,
                "top_p": 1
            }
        )
        return response.json()

# ================== HELPER METHODS ==================
async def broadcast(message: str, store_if_offline=False):
    if connected_clients:
        for ws in connected_clients.copy():
            try:
                await ws.send_str(message)
            except:
                connected_clients.discard(ws)
    elif store_if_offline:
        pending_messages.append(message)

async def call_self():
    web_socket_url = os.environ.get("WEB_SOCKET_URL", "ws://localhost:10000")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(web_socket_url, data="ping")
    except Exception as e:
        print(f"call_self error: {e}")

# ================== MESSAGE PROCESSING ==================
async def process_message(message: str) -> str:
    try:
        data = json.loads(message)
        msg_type = data.get("type")
        if msg_type == "login" and data.get("provider") == "google":
            return "🔑 Google login requested, send me the token."
        if msg_type == "token" and data.get("provider") == "google":
            token = data.get("token")
            return f"✅ Google token received: {token[:10]}..."
        return "⚠️ Unknown JSON message type."
    except json.JSONDecodeError:
        try:
            res = await groq_respond(message)
            return res["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"Groq error: {str(e)}"

# ================== WEBSOCKET HANDLER ==================
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    connected_clients.add(ws)
    for msg in pending_messages:
        await ws.send_str(f"(📬 Missed) {msg}")
    pending_messages.clear()

    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            reply = await process_message(msg.data)
            await ws.send_str(reply)

    connected_clients.discard(ws)
    return ws

# ================== HTTP HANDLER ==================
async def http_handler(request):
    return web.Response(text="Server is running ✅")


# ================== RUN ==================
if __name__ == "__main__":
    asyncio.run(main())
