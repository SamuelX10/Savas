import os
import asyncio
import websockets
import requests

# ================= WebSocket clients =================
connected_clients = set()

# ================= GPT via HTTP request =================
def call_gpt_http(prompt: str) -> str:
    """Calls OpenAI GPT-3.5-turbo via HTTP POST."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "⚠️ GPT API key not set!"

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are Savas Brain, a helpful AI assistant."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        return f"⚠️ GPT HTTP Error: {str(e)}"
    except Exception as e:
        return f"⚠️ Unexpected Error: {str(e)}"

# ================= Brain logic =================
async def process_message(message: str) -> str:
    """Processes incoming messages and sends to GPT via HTTP."""
    # Test shortcut
    if isinstance(message, str) and message.strip().lower() == "test":
        return "🧪 Test successful! WebSocket is working."

    # Call GPT asynchronously in a separate thread
    return await asyncio.to_thread(call_gpt_http, message)

# ================= WebSocket handler =================
async def handler(websocket):
    """Handles new WebSocket connections and incoming messages."""
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            print("Message received:", message)
            reply = await process_message(message)
            await websocket.send(reply)
    finally:
        connected_clients.remove(websocket)

# ================= Main server =================
async def main():
    """Starts the WebSocket server on Render dynamic port."""
    PORT = int(os.environ.get("PORT", 10000))
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"Brain is running on port {PORT}...")
        await asyncio.Future()  # run forever

# ================= Run server =================
if __name__ == "__main__":
    asyncio.run(main())