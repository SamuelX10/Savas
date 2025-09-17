import os
import asyncio
import websockets
from openai import OpenAI

# ================= Temporary API Key for Testing =================
# ⚠️⚠️⚠️ DANGER ZONE! REMOVE THIS LINE BEFORE DEPLOYMENT! ⚠️⚠️⚠️
# Use this only for quick debugging. Uncomment the line below and paste your key.
# temp_api_key = "YOUR_OPENAI_API_KEY_GOES_HERE" 

# ================= WebSocket clients =================
connected_clients = set()

# ================= GPT-3.5 call =================
async def gpt_response(message: str) -> str:
    """Handles the API call to OpenAI's GPT-3.5 model."""
    # Use the temporary key if it's set, otherwise use the environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    # If you uncommented the temporary key, it will override the environment variable
    # if 'temp_api_key' in locals():
    #     api_key = temp_api_key
    
    # We still keep the original check to be safe
    if not api_key:
        return "⚠️ GPT API key not set!"

    try:
        def blocking_call():
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are Savas Brain, a helpful AI assistant."},
                    {"role": "user", "content": message}
                ]
            )
            return response.choices[0].message.content.strip()

        return await asyncio.to_thread(blocking_call)

    except Exception as e:
        print(f"GPT API call failed with a new error: {e}")
        return f"⚠️ GPT Error: {str(e)}"

# ================= Brain logic =================
async def process_message(message: str) -> str:
    """Processes incoming messages and determines the appropriate response."""
    # We put everything in a try...except block to catch anything unexpected
    try:
        # ✅ Test shortcut — still using .strip() for robust handling of spaces.
        if isinstance(message, str) and message.strip().lower() == "test":
            return "🧪 Test successful! WebSocket is working."

        # All other messages go to GPT-3.5
        return await gpt_response(message)
        
    except Exception as e:
        # If any unexpected error happens in this logic, we will catch it here
        print(f"Error in process_message: {e}")
        return f"⚠️ Unexpected Error: {str(e)}"


# ================= WebSocket handler =================
async def handler(websocket):
    """Handles new WebSocket connections and message reception."""
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
    """Starts the WebSocket server on the specified port."""
    PORT = int(os.environ.get("PORT", 10000))
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"Brain is running on port {PORT}...")
        await asyncio.Future()  # run forever

# ================= Run server =================
if __name__ == "__main__":
    asyncio.run(main())
