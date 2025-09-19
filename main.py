import os
import json
import asyncio
from aiohttp import web
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

scheduler = None

# ============= GROQ CONFIG ============
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "groq/compound"

# ============= GROQ HELPER ============
async def groq_respond(msg: str):
    """
    Send message to Groq API and return parsed JSON.
    Raises Exception on network/parse errors.
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set in environment")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": msg}],
        "temperature": 1,
        "max_tokens": 1024,
        "top_p": 1
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(GROQ_API_URL, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()

# ============= PROCESS MESSAGE ============
async def process_message(message: str) -> str:
    """
    Process an incoming text message and return a reply string.
    Uses Groq; falls back to a friendly error message if Groq fails.
    """
    try:
        # call Groq
        res = await groq_respond(message)

        # Try common response shapes safely
        #  - expected: res["choices"][0]["message"]["content"]
        # Use robust access with defaults
        choices = res.get("choices") if isinstance(res, dict) else None
        if choices and isinstance(choices, list) and len(choices) > 0:
            first = choices[0]
            # Try different possible shapes
            content = None
            if isinstance(first, dict):
                # shape: {"message": {"content": "..."}}
                message_obj = first.get("message")
                if isinstance(message_obj, dict):
                    content = message_obj.get("content")
                # or shape: {"text": "..."} (fallback)
                if not content:
                    content = first.get("text")
            if content:
                return content.strip()

        # Last fallback: try top-level fields or return raw JSON
        if isinstance(res, dict):
            # try 'text' at top level or 'response' etc.
            for key in ("text", "response", "reply"):
                if key in res and isinstance(res[key], str):
                    return res[key].strip()
            # otherwise return a summarized JSON (not too long)
            return json.dumps(res)[:200] + "..."
        else:
            return str(res)

    except Exception as e:
        # Keep the user informed, but don't leak internal stack traces
        return f"Groq error: {str(e)}"

# ============= ROOT POST (chat) ============
async def root_handler(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    message = data.get("message")
    if not message:
        return web.json_response({"error": "Missing 'message' field"}, status=400)

    reply = await process_message(message)
    return web.json_response({"reply": reply})

# ============= AUTH HANDLER (POST /auth/) ============
async def handle_google_auth_code(server_auth_code: str):
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "postmessage")
    GOOGLE_TOKEN_URI = os.environ.get("GOOGLE_TOKEN_URI")
    
    if not server_auth_code:
        return {"error": "Missing serverAuthCode"}

    payload = {
        "code": server_auth_code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(GOOGLE_TOKEN_URI, data=payload)
            if res.status_code != 200:
                print("Google error response:", res.text)  # 👈 debug log
            res.raise_for_status()
            token_data = res.json()
        return token_data
    except Exception as e:
        return {"error": str(e)}


async def auth_handler(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    provider = data.get("provider")
    if not provider:
        return web.json_response({"error": "Missing provider"}, status=400)

    if provider == "google":
        server_auth_code = data.get("code")
        token_data = await handle_google_auth_code(server_auth_code)
        return web.json_response(token_data)

    return web.json_response({"error": f"Unsupported provider: {provider}"}, status=400)

# ============= SERVER STARTUP ============
async def start_server():
    app = web.Application()
    app.add_routes([
        web.post("/", root_handler),      # POST / for chat
        web.post("/auth/", auth_handler), # POST /auth/ for auth providers
        web.get("/server_status", lambda r: web.Response(text="Server is running"))
    ])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    print(f"Server started on port {port}")
    await site.start()

    while True:
        await asyncio.sleep(3600)

async def main():
    global scheduler
    scheduler = AsyncIOScheduler()
    scheduler.start()
    await start_server()

if __name__ == "__main__":
    asyncio.run(main())
