import os
import asyncio
import websockets
from openai import OpenAI

# ================= WebSocket clients =================
connected_clients = set()

# ================= GPT-3.5 call =================
async def gpt_response(message: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "⚠️ GPT API key not set!"

    try:
        # Run GPT in a separate thread to avoid blocking WebSocket loop
        def blocking_call():
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # switched to GPT-3.5
                messages=[
                    {"role": "system", "content": "You are Savas Brain, a helpful AI assistant."},
                    {"role": "user", "content": message}
                ]
            )
            return response.choices[0].message.content.strip()

        return await asyncio.to_thread(blocking_call)

    except Exception as e:
        return f"⚠️ GPT Error: {str(e)}"

# ================= Brain logic =================
async def process_message(message: str) -> str:
    # ✅ Test shortcut — never calls GPT
    if message.lower() == "test":
        return "🧪 Test successful! WebSocket is working."

    # All other messages go to GPT-3.5
    return await gpt_response(message)

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