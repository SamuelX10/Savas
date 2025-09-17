import os
import asyncio
import websockets

# ================= WebSocket clients =================
connected_clients = set()

# ================= Brain logic =================
async def process_message(message: str) -> str:
    # ✅ Test shortcut
    if message.lower() == "test":
        return "🧪 Test successful! WebSocket is working."
    
    # Echo everything else
    return f"Echo: {message}"

# ================= WebSocket handler =================
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
    PORT = int(os.environ.get("PORT", 10000))  # Render dynamic port
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"Brain is running on port {PORT}...")
        await asyncio.Future()  # run forever

# ================= Run server =================
if __name__ == "__main__":
    asyncio.run(main())