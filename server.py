import os
import asyncio
import websockets
import json

PORT = 8000

async def handler(websocket, path):
    async for message in websocket:
        print(f"📩 Received: {message}")

        if message.strip().lower() == "test":
            api_key = os.getenv("OPENAI_API_KEY", "NOT FOUND")
            response = f"🔑 API Key from env: {api_key}"
        else:
            response = f"echo: {message}"

        await websocket.send(response)

async def main():
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"✅ WebSocket server running on ws://0.0.0.0:{PORT}")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())