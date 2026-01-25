from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, Set, List
import json
import asyncio
from app.auth.jwt import decode_token
from app.db.database import AsyncSessionLocal
from app.models.models import ChatMessage, Tenant
from sqlalchemy import select, desc
from datetime import datetime
import os

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

async def get_chat_history(tenant_id: int, limit: int = 20, offset: int = 0) -> List[dict]:
    """Load chat messages from database with pagination"""
    print(f"[DEBUG] get_chat_history called with tenant_id={tenant_id}, limit={limit}, offset={offset}")
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ChatMessage)
            .where(ChatMessage.tenant_id == tenant_id)
            .order_by(desc(ChatMessage.timestamp))
            .limit(limit)
            .offset(offset)
        )
        messages = result.scalars().all()
        print(f"[DEBUG] Query returned {len(messages)} messages")
        msg_list = [
            {
                "sender": msg.sender,
                "message": msg.message,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                "metadata": msg.meta_data
            }
            for msg in reversed(messages)
        ]
        print(f"[DEBUG] Returning {len(msg_list)} messages after reversal")
        return msg_list

async def save_chat_message(tenant_id: int, sender: str, message: str, metadata: dict = None):
    """Save a chat message to database with optional embedding"""
    async with AsyncSessionLocal() as session:
        # Generate embedding if OpenAI is available
        embedding_str = None
        try:
            from openai import AsyncOpenAI
            from app.config import settings
            
            if settings.OPENAI_API_KEY or settings.AZURE_OPENAI_KEY:
                if settings.OPENAI_API_TYPE == "azure" and settings.AZURE_OPENAI_ENDPOINT:
                    client = AsyncOpenAI(
                        api_key=settings.AZURE_OPENAI_KEY,
                        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                        api_version="2024-02-15-preview"
                    )
                    model = "text-embedding-ada-002"  # Your Azure deployment name
                else:
                    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                    model = "text-embedding-3-small"
                
                response = await client.embeddings.create(
                    model=model,
                    input=message
                )
                embedding = response.data[0].embedding
                embedding_str = json.dumps(embedding)  # Store as JSON string
        except Exception as e:
            print(f"Embedding generation failed: {e}")
        
        chat_msg = ChatMessage(
            tenant_id=tenant_id,
            sender=sender,
            message=message,
            meta_data=metadata,
            embedding=embedding_str
        )
        session.add(chat_msg)
        await session.commit()

async def get_cloud_resources_summary(tenant_id: int) -> dict:
    """Fetch real-time cloud resource details for AI context"""
    from app.api.v1.metrics import fetch_aws_resources, fetch_azure_resources, fetch_gcp_resources
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            return {"error": "Tenant not found"}
        
        meta = tenant.metadata_json or {}
        provider = (meta.get("provider") or "aws").lower()
        
        # Fetch full resource details based on provider
        if provider == "aws":
            resources = await fetch_aws_resources(tenant_id, meta)
        elif provider == "azure":
            resources = await fetch_azure_resources(tenant_id, meta)
        elif provider == "gcp":
            resources = await fetch_gcp_resources(tenant_id, meta)
        else:
            return {"error": "Unknown provider"}
        
        # Return full resource details for AI to analyze
        return {
            "provider": provider,
            "tenant_name": tenant.name,
            "resources": resources
        }

async def generate_ai_response(tenant_id: int, user_message: str, history: List[dict]) -> str:
    """Generate AI response using OpenAI with function calling for cloud resources"""
    try:
        from openai import AsyncOpenAI
        from app.config import settings
        
        # Check if API key is configured
        api_key = None
        if settings.OPENAI_API_TYPE == "azure":
            if not settings.AZURE_OPENAI_KEY or "replace" in settings.AZURE_OPENAI_KEY.lower():
                return "Azure OpenAI API key not configured. Please set AZURE_OPENAI_KEY environment variable."
            api_key = settings.AZURE_OPENAI_KEY
        else:
            if not settings.OPENAI_API_KEY or "replace" in settings.OPENAI_API_KEY.lower() or settings.OPENAI_API_KEY == "sk-":
                return "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable to your OpenAI API key from https://platform.openai.com/account/api-keys"
            api_key = settings.OPENAI_API_KEY
        
        # Initialize OpenAI client
        if settings.OPENAI_API_TYPE == "azure" and settings.AZURE_OPENAI_ENDPOINT:
            client = AsyncOpenAI(
                api_key=api_key,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_version="2024-02-15-preview"
            )
            model = "gpt-4"  # Your Azure deployment name
        else:
            client = AsyncOpenAI(api_key=api_key)
            model = "gpt-4o-mini"
        
        # Build conversation context
        messages = [
            {
                "role": "system",
                "content": """You are a helpful cloud infrastructure assistant. You can answer questions about AWS, Azure, and GCP resources.
When users ask about their cloud resources (VMs, databases, storage, etc.), use the get_cloud_resources function to fetch real-time data.
Be concise and helpful. Format numbers and lists clearly."""
            }
        ]
        
        # Add recent history (last 10 messages)
        for msg in history[-10:]:
            messages.append({
                "role": "user" if msg["sender"] == "user" else "assistant",
                "content": msg["message"]
            })
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Define function for fetching cloud resources
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_cloud_resources",
                    "description": "Get detailed real-time cloud resources (VMs, databases, storage, etc.) with full properties including OS type, names, versions, configurations, and current state. Use this to answer questions about specific resources and their details.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]
        
        # First API call
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        
        # Check if function was called
        if response_message.tool_calls:
            # Execute function
            for tool_call in response_message.tool_calls:
                if tool_call.function.name == "get_cloud_resources":
                    function_response = await get_cloud_resources_summary(tenant_id)
                    
                    # Add function response to conversation
                    messages.append(response_message)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(function_response)
                    })
            
            # Second API call with function result
            second_response = await client.chat.completions.create(
                model=model,
                messages=messages
            )
            return second_response.choices[0].message.content
        
        return response_message.content
        
    except ImportError:
        return "OpenAI package not installed. Please install: pip install openai"
    except Exception as e:
        error_str = str(e)
        print(f"AI generation error: {e}")
        # Provide helpful error messages
        if "invalid_api_key" in error_str.lower() or "401" in error_str:
            return "Invalid or missing OpenAI API key. Please set OPENAI_API_KEY environment variable with your valid API key from https://platform.openai.com/account/api-keys"
        elif "rate_limit" in error_str.lower():
            return "OpenAI API rate limit exceeded. Please try again in a moment."
        else:
            return f"I'm having trouble processing your request. Please ensure your OpenAI API key is valid: {error_str[:100]}"

@router.get("/history/{client_id}")
async def get_history(client_id: int):
    """REST endpoint to get chat history for a client"""
    try:
        history = await get_chat_history(client_id, limit=100)
        return {"messages": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    
    # Send initial chat history on connection (most recent 20 messages)
    try:
        history = await get_chat_history(int(client_id), limit=20, offset=0)
        print(f"[WebSocket] Loading {len(history)} messages for client {client_id}")
        await websocket.send_json({
            "type": "history",
            "messages": history,
            "hasMore": len(history) == 20  # If we got full page, there might be more
        })
        print(f"[WebSocket] Sent {len(history)} messages to client {client_id}, hasMore={len(history) == 20}")
    except Exception as e:
        print(f"Error loading chat history: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            if not user_message:
                continue
            
            # Save user message
            await save_chat_message(int(client_id), "user", user_message)
            
            # Echo user message to all connections
            response = {
                "type": "message",
                "clientId": client_id,
                "message": user_message,
                "timestamp": datetime.utcnow().isoformat(),
                "sender": "user"
            }
            await manager.broadcast(response, client_id)
            
            # Generate AI response
            try:
                history = await get_chat_history(int(client_id), limit=20, offset=0)
                ai_response = await generate_ai_response(int(client_id), user_message, history)
                
                # Save AI response
                await save_chat_message(int(client_id), "assistant", ai_response)
                
                # Send AI response
                bot_response = {
                    "type": "message",
                    "clientId": client_id,
                    "message": ai_response,
                    "timestamp": datetime.utcnow().isoformat(),
                    "sender": "assistant"
                }
                await manager.broadcast(bot_response, client_id)
                
            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {str(e)}"
                await manager.broadcast({
                    "type": "message",
                    "clientId": client_id,
                    "message": error_msg,
                    "timestamp": datetime.utcnow().isoformat(),
                    "sender": "assistant"
                }, client_id)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
    except Exception as e:
        manager.disconnect(websocket, client_id)


@router.get("/history/{tenant_id}")
async def get_history(
    tenant_id: int,
    limit: int = 20,
    offset: int = 0,
    token: dict = Depends(decode_token)
):
    """
    Get paginated chat history for a tenant.
    Returns messages in chronological order (oldest first within the page).
    """
    try:
        messages = await get_chat_history(tenant_id, limit=limit, offset=offset)
        return {
            "messages": messages,
            "limit": limit,
            "offset": offset,
            "count": len(messages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
