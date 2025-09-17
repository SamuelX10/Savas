import os
import asyncio
import websockets
from openai import OpenAI

# ================= Initialize GPT client =================
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ================= Brain logic using GPT =================
async def process_message(message: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # or gpt-3.5-turbo for cheaper
            messages=[
                {"role": "system", "content": "You are Savas Brain, a helpful AI assistant."},
                {"role": "user", "content": message}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# ================= WebSocket handler =================
connected_clients = set()  # Track connected clients

async def handler(websocket):
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
    PORT = int(os.environ.get("PORT", 10000))  # Render uses dynamic ports
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"Brain is running on port {PORT}...")
        await asyncio.Future()  # run forever

# ================= Run server =================
asyncio.run(main())