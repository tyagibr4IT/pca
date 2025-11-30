from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import json
import asyncio
from app.auth.jwt import decode_token

router = APIRouter(prefix="/chat", tags=["chat"])

# Store active WebSocket connections per client
active_connections: Dict[str, Set[WebSocket]] = {}

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = set()
        self.active_connections[client_id].add(websocket)

    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            self.active_connections[client_id].discard(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]

    async def broadcast(self, message: dict, client_id: str):
        """Broadcast message to all connections for a specific client"""
        if client_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[client_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.add(connection)
            
            # Remove disconnected clients
            for connection in disconnected:
                self.active_connections[client_id].discard(connection)

manager = ConnectionManager()

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time chat per client (requires JWT)"""
    # Try to get token from 'authorization' header or query string 'token'
    auth_header = websocket.headers.get('authorization') or websocket.headers.get('Authorization')
    token = None
    if auth_header and auth_header.lower().startswith('bearer '):
        token = auth_header.split(' ', 1)[1]
    else:
        # Fallback to query param
        token = websocket.scope.get('query_string', b'').decode('utf-8')
        if token:
            # parse token=...
            for part in token.split('&'):
                if part.startswith('token='):
                    token = part.split('=',1)[1]
                    break
                else:
                    token = None
    if not token or decode_token(token) is None:
        await websocket.close(code=4401)  # 4401: Unauthorized
        return

    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Echo message back to all connections for this client
            response = {
                "type": "message",
                "clientId": client_id,
                "message": message_data.get("message", ""),
                "timestamp": message_data.get("timestamp", ""),
                "sender": message_data.get("sender", "user")
            }
            
            await manager.broadcast(response, client_id)
            
            # Simulate a bot response after 1 second (optional demo)
            if message_data.get("sender") == "user":
                await asyncio.sleep(1)
                bot_response = {
                    "type": "message",
                    "clientId": client_id,
                    "message": f"Auto-reply: Received '{message_data.get('message', '')}'",
                    "timestamp": "",
                    "sender": "bot"
                }
                await manager.broadcast(bot_response, client_id)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
    except Exception as e:
        manager.disconnect(websocket, client_id)
