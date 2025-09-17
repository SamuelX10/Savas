import os
import asyncio
import websockets

async def handler(websocket, path):
    async for message in websocket:
        
        if message.strip().lower() == "test":
            api_key = os.getenv("OPENAI_API_KEY", "NOT FOUND")
            response = f"🔑 API Key from env: {api_key}"
        
        await websocket.send(response)

async def main():
    # ✅ Use Render's dynamic port
    PORT = int(os.environ.get("PORT", 10000))  
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"✅ WebSocket server running on ws://0.0.0.0:{PORT}")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())