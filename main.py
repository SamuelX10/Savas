import os
import asyncio
import websockets
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

# ================== GLOBALS ==================
scheduler = None
connected_clients = set()
pending_messages = []  # missed messages when no client is online
routine_pairs = []     # store routines as [("08:00", "Morning News"), ...]


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
        scheduler.add_job(scheduled_task, "cron", hour=hour, minute=minute, args=[task])


async def start_server():
    PORT = int(os.environ.get("PORT", 10000))
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"🧠 Brain with Scheduler running on port {PORT}...")
        await asyncio.Future()


# ================== HELPERS ==================
async def broadcast(message: str, store_if_offline=False):
    """Send a message to all connected clients, or store if none are online."""
    if connected_clients:
        for ws in connected_clients.copy():
            try:
                await ws.send(message)
            except:
                connected_clients.remove(ws)
    elif store_if_offline:
        pending_messages.append(message)


# ================== FETCH NEWS ==================
def fetch_news():
    await broadcast(store_if_offline=True)
    
    news_api_key = os.environ.get("NEWS_API_KEY")
    if not news_api_key:
        return "⚠️ NEWS_API_KEY not set!"

    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "country": "ng",   
        "pageSize": 3,
        "apiKey": news_api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        articles = response.json().get("articles", [])

        if not articles:
            return "⚠️ No news found today."

        headlines = [f"- {a['title']}" for a in articles[:3]]
        return "📰 Morning News:\n" + "\n".join(headlines)

    except Exception as e:
        return f"⚠️ News fetch error: {str(e)}"
        

async def scheduled_task(message: str):
    await broadcast(f"⏰ Reminder: {message}")


async def call_self():
    """Simulate self-calling every 13 minutes"""
    await broadcast("🔁 Self-check triggered at " + str(datetime.now()))


# ================== MESSAGE HANDLER ==================
async def process_message(message: str) -> str:
    
    return f"echo: {message}"


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
        connected_clients.remove(websocket)

if __name__ == "__main__":
    asyncio.run(main())
