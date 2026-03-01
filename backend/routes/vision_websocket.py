"""
WebSocket endpoint for real-time Vision Agents interview updates.

This module provides WebSocket connections for streaming live interview
state updates to the frontend.
"""

import json
import logging
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.websockets import WebSocketState

logger = logging.getLogger(__name__)

router = APIRouter()

# Active WebSocket connections per session
active_connections: Dict[str, Set[WebSocket]] = {}


class ConnectionManager:
    """
    Manages WebSocket connections for live interview sessions.
    
    Features:
    - Multiple clients per session
    - Broadcast to all clients in a session
    - Automatic cleanup on disconnect
    """
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """
        Accept WebSocket connection and add to session.
        
        Args:
            websocket: WebSocket connection
            session_id: Session identifier
        """
        await websocket.accept()
        
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        
        self.active_connections[session_id].add(websocket)
        logger.info(f"WebSocket connected for session {session_id}")
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        """
        Remove WebSocket connection from session.
        
        Args:
            websocket: WebSocket connection
            session_id: Session identifier
        """
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            
            # Clean up empty session
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        
        logger.info(f"WebSocket disconnected for session {session_id}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send message to specific WebSocket.
        
        Args:
            message: Message dictionary
            websocket: Target WebSocket
        """
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
    
    async def broadcast_to_session(self, message: dict, session_id: str):
        """
        Broadcast message to all clients in a session.
        
        Args:
            message: Message dictionary
            session_id: Session identifier
        """
        if session_id not in self.active_connections:
            return
        
        disconnected = set()
        
        for websocket in self.active_connections[session_id]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
                else:
                    disconnected.add(websocket)
            except Exception as e:
                logger.error(f"Failed to broadcast to websocket: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket, session_id)
    
    def get_connection_count(self, session_id: str) -> int:
        """
        Get number of active connections for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Number of active connections
        """
        return len(self.active_connections.get(session_id, set()))


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/interview/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str
):
    """
    WebSocket endpoint for live interview updates.
    
    Message Types:
    - state_change: Full state update
    - confidence_update: Emotion/confidence update
    - question_asked: New question notification
    - interview_complete: Interview completion notification
    
    Args:
        websocket: WebSocket connection
        session_id: Session identifier
    """
    await manager.connect(websocket, session_id)
    
    try:
        # Send initial connection confirmation
        await manager.send_personal_message({
            "type": "connected",
            "session_id": session_id,
            "message": "WebSocket connected successfully"
        }, websocket)
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive messages from client (e.g., ping/pong)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle ping
                if message.get("type") == "ping":
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": message.get("timestamp")
                    }, websocket)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client: {data}")
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                break
    
    finally:
        manager.disconnect(websocket, session_id)


async def broadcast_state_change(session_id: str, state: dict):
    """
    Broadcast state change to all clients in a session.
    
    Args:
        session_id: Session identifier
        state: Current session state
    """
    await manager.broadcast_to_session({
        "type": "state_change",
        "state": state
    }, session_id)


async def broadcast_confidence_update(session_id: str, emotion: dict):
    """
    Broadcast confidence/emotion update to all clients.
    
    Args:
        session_id: Session identifier
        emotion: Emotion data dictionary
    """
    await manager.broadcast_to_session({
        "type": "confidence_update",
        "emotion": emotion
    }, session_id)


async def broadcast_question_asked(session_id: str, question: dict):
    """
    Broadcast new question notification.
    
    Args:
        session_id: Session identifier
        question: Question data dictionary
    """
    await manager.broadcast_to_session({
        "type": "question_asked",
        "question": question
    }, session_id)


async def broadcast_interview_complete(session_id: str):
    """
    Broadcast interview completion notification.
    
    Args:
        session_id: Session identifier
    """
    await manager.broadcast_to_session({
        "type": "interview_complete",
        "session_id": session_id
    }, session_id)


async def broadcast_speech_metrics_update(session_id: str, metrics: dict):
    """
    Broadcast speech metrics update to all clients.
    
    Args:
        session_id: Session identifier
        metrics: Speech metrics dictionary (filler_count, pace, pauses)
    """
    await manager.broadcast_to_session({
        "type": "speech_metrics_update",
        "metrics": metrics
    }, session_id)


async def broadcast_ai_state_change(session_id: str, ai_state: str):
    """
    Broadcast AI state change (listening/thinking/speaking).
    
    Args:
        session_id: Session identifier
        ai_state: New AI state
    """
    await manager.broadcast_to_session({
        "type": "ai_state_change",
        "ai_state": ai_state
    }, session_id)


async def broadcast_ai_audio(session_id: str, audio_base64: str):
    """
    Broadcast AI-generated audio to all clients.
    
    Args:
        session_id: Session identifier
        audio_base64: Base64-encoded audio data
    """
    await manager.broadcast_to_session({
        "type": "ai_audio",
        "audio": {
            "data": audio_base64,
            "format": "mp3"
        }
    }, session_id)


def get_connection_manager() -> ConnectionManager:
    """
    Get the global connection manager instance.
    
    Returns:
        ConnectionManager instance
    """
    return manager
