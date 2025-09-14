import os
import asyncio
import websockets

# Simple "brain" logic
async def process_message(message: str) -> str:
    if message.lower() == "hello":
        return "Hi Samuel 👋, I am Savas Brain!"
    elif message.lower() == "play music":
        return "🎶 Playing music..."
    elif message.lower().startswith("search "):
        query = message[7:]
        return f"🔍 I would search online for: {query}"
    else:
        return "I don’t understand 🤔"

# WebSocket handler
async def handler(websocket):
    async for message in websocket:
        print("Savas said:", message)
        reply = await process_message(message)
        await websocket.send(reply)

async def main():
    PORT = int(os.environ.get("PORT", 10000))  # Get port from environment
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"Brain is running on port {PORT}...")
        await asyncio.Future()  # run forever

asyncio.run(main())
