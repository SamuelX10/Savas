import os
import json
import asyncio
import logging
from aiohttp import web, WSMsgType
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from util.ServerUtil import ServerUtil
from util.GroqUtil import GroqUtil
from util.AssistantUtil import AssistantUtil

load_dotenv()
scheduler = None
ASSISTANT_TOOLS = {}

# ===== In-memory device state storage =====
CONNECTED_DEVICES = {}
DEVICE_STATES = {}

# ===== TOOL REGISTRATION =====
def register_tool(name):
    """Decorator to register tools dynamically."""
    def wrapper(func):
        ASSISTANT_TOOLS[name] = func
        return func
    return wrapper


# ===== PROCESS MESSAGE =====
async def process_message(message: str) -> str:
    try:
        access_token = await ServerUtil.get_google_access_token()
        profile = await ServerUtil.get_google_user_info(access_token)
        given_name = profile.get("given_name", "Samuel")

        # Ask Groq for intent
        intent_prompt = {
            "role": "system",
            "content": """You are an intent router.
Available tools: get_google_tasks, get_google_calendar.
If user asks about tasks → {"action": "get_google_tasks"}.
If user asks about schedule/calendar → {"action": "get_google_calendar"}.
Otherwise → {"action":"chat"}.
Return ONLY JSON, no text."""
        }
        intent_raw = await GroqUtil.prompt(intent_prompt, message)
        try:
            intent = json.loads(intent_raw)
        except:
            intent = {"action": "chat"}

        if intent[ = {
                "role": "system",
                "content": f"You are {given_name}'s Jarvis-like AI.\n"
                           f"User asked: '{message}'\n"
                           f"Tool output:\n{json.dumps(tool_result, indent=2)}\n"
                           f"Now respond naturally, call him 'Sir'."
            }
            return await GroqUtil.prompt(final_prompt, message)

        # Normal chat fallback
        chat_prompt = {
            "role": "system",
            "content": f"You are {given_name}'s personal AI assistant (Jarvis style). Always helpful and call him 'Sir'."
        }
        return await GroqUtil.prompt(chat_prompt, message)

    except Exception as e:
        return f"Error: {str(e)}"



# ===== HANDLERS =====
async def device_handler(request: web.Request) -> web.WebSocketResponse:
    """WebSocket endpoint for devices to send updates."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    device_id = request.query.get("device_id")
    device_type = request.query.get("device_type")

    if not device_id or not device_type:
        await ws.close()
        return ws

    CONNECTED_DEVICES[device_id] = ws
    logging.info(f"[WS] Device connected: {device_id} ({device_type})")

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue

                data["device_id"] = device_id
                data["device_type"] = device_type
                data["last_seen"] = asyncio.get_event_loop().time()

                DEVICE_STATES[device_id] = data
                logging.info(f"[Device Update] {device_id}: {data}")

                # Push commands back to device if needed
                if "new_wallpaper" in data:
                    await ws.send_json({
                        "type": "wallpaper_update",
                        "url": data["new_wallpaper"]
                    })
            elif msg.type == WSMsgType.ERROR:
                logging.warning(f"[WS] Error: {ws.exception()}")

    finally:
        CONNECTED_DEVICES.pop(device_id, None)
        logging.info(f"[WS] Device disconnected: {device_id}")

    return ws

async def chat_handler(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        message = data.get("data", "")
        if not message:
            return web.json_response({"error": "Data is required"}, status=400)

        reply = await process_message(message)
        return web.json_response({"data": reply})

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def user_handler(request: web.Request) -> web.Response:
    try:
        access_token = await ServerUtil.get_google_access_token()
        user_info = await ServerUtil.get_google_user_info(access_token)
        return web.json_response({"data": user_info})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def root_handler(request):
    return web.json_response({"status": "ok"})


# ===== MAIN ENTRY POINT =====
async def keep_server_alive():
    RENDER_SERVER_URL = os.environ.get("RENDER_SERVER_URL", "")
    payload = {"data": "Server is running"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(RENDER_SERVER_URL, json=payload)
    except Exception:
        pass

async def start_server():
    app = web.Application()
    app.add_routes([
        web.post("/chat", chat_handler),
        web.get("/device", device_handler),
        web.get("/user", user_handler),
        web.get("/", root_handler),
    ])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    global scheduler
    scheduler = AsyncIOScheduler()
    scheduler.start()

    await start_server()
    scheduler.add_job(lambda: asyncio.create_task(keep_server_alive()), 'interval', minutes=1)

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
