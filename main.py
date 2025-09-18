import os
import asyncio
import websockets
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

# ================== GLOBALS ==================
scheduler = None
connected_clients = set()
pending_messages = []  # missed messages when no client is online
routine_pairs = []     # store routines as [("08:00", "Morning News"), ...]

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "groq/compound"  # You can change to other available models

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# Lambda for Groq API chat completion
groq_respond = lambda msg: asyncio.to_thread(
    lambda: httpx.post(
        GROQ_API_URL,
        headers=headers,
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": msg}]
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
    global scheduler, routine_pairs
    scheduler = AsyncIOScheduler()

    # Example routine pairs (time, task)
    routine_pairs = [
        ("08:00", "Morning News"),
        ("13:00", "Lunch Reminder"),
        ("20:00", "Night Reflection"),
    ]


def initialize_logic():
    # Start the scheduler
    scheduler.start()

    # Self-calling job every 13 minutes
    scheduler.add_job(call_self, "interval", minutes=13)
    
    # Load routines into scheduler
    for time_str, task in routine_pairs:
        hour, minute = map(int, time_str.split(":"))
        if task == "Morning News":
            scheduler.add_job(fetch_news, "cron", hour=hour, minute=minute)
        else:
            scheduler.add_job(scheduled_task, "cron", hour=hour, minute=minute, args=[task])


async def start_server():
    PORT = int(os.environ.get("PORT", 10000))
    async with websockets.serve(handler, "0.0.0.0", PORT):
        await asyncio.Future()


# ================== HELPERS ==================
async def broadcast(message: str, store_if_offline=False):
    """Send a message to all connected clients, or store if none are online."""
    if connected_clients:
        for ws in connected_clients.copy():
            try:
                await ws.send(message)
            except:
                connected_clients.discard(ws)
    elif store_if_offline:
        pending_messages.append(message)


# ================== FETCH NEWS ==================
async def fetch_news():
    news_api_key = os.environ.get("NEWS_API_KEY")
    if not news_api_key:
        msg = "⚠️ NEWS_API_KEY not set!"
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
            msg = "⚠️ No news found today."
        else:
            headlines = [f"- {a['title']}" for a in articles[:3]]
            msg = "📰 Morning News:\n" + "\n".join(headlines)
    except Exception as e:
        msg = f"⚠️ News fetch error: {str(e)}"
    
    await broadcast(msg, store_if_offline=True)
    

async def call_self():
    web_socket_url = os.environ.get("WEB_SOCKET_URL")
    try:
        async with websockets.connect(web_socket_url) as websocket:
            await websocket.send("ping")
            await websocket.recv()
    except Exception as e:
        

        async def scheduled_task(message: str):
    await broadcast(f"⏰ Reminder: {message}")


# ================== MESSAGE HANDLER ==================
async def process_message(message: str) -> str:
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


if __name__ == "__main__":
    asyncio.run(main())
