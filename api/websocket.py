from fastapi import WebSocket, APIRouter
from fastapi.responses import HTMLResponse

from core.server import read_server_log

ws = APIRouter(tags=["websocket"])


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/api/wslog");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


@ws.get("/wsclient")
async def get():
    return HTMLResponse(html)


@ws.websocket('/wslog')
async def send_server_log(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await read_server_log()
        await websocket.send_text(f"server: {data}")