import os
import asyncio
import websockets
import requests

# ================= WebSocket clients =================
connected_clients = set()

# ================= Test API call =================
async def test_api_response(message: str) -> str:
    """Handles a simple API call to a test endpoint."""
    try:
        # Use asyncio.to_thread to run a synchronous requests call in a separate thread
        def blocking_call():
            # A simple public API that returns a list of posts. We get the first one.
            response = requests.get("https://jsonplaceholder.typicode.com/posts/1")
            response.raise_for_status()  # Raise an exception for bad status codes
            
            # We will return the title of the post as a test response
            data = response.json()
            return f"✅ Test API Response: {data.get('title')}"

        return await asyncio.to_thread(blocking_call)

    except requests.exceptions.RequestException as e:
        print(f"Test API call failed with a new error: {e}")
        return f"⚠️ Test API Error: {str(e)}"
    except Exception as e:
        print(f"Unexpected error in test_api_response: {e}")
        return f"⚠️ Unexpected Error: {str(e)}"

# ================= Brain logic =================
async def process_message(message: str) -> str:
    """Processes incoming messages and determines the appropriate response."""
    try:
        # ✅ Test shortcut — still using .strip() for robust handling of spaces.
        if isinstance(message, str) and message.strip().lower() == "test":
            return "🧪 Test successful! WebSocket is working."

        # All other messages go to the new test API
        return await test_api_response(message)
        
    except Exception as e:
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
