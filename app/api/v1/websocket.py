import asyncio
import json
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.redis import get_redis

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.websocket("/ws/submissions/{submission_id}")
async def submission_websocket_endpoint(websocket: WebSocket, submission_id: int):
    """
    Persistent WebSocket endpoint for real-time submission evaluation streaming.
    Listens on Redis Pub/Sub channel 'submission_{submission_id}' and relays events.
    """
    await websocket.accept()
    await websocket.send_json({"event": "CONNECTED", "submission_id": submission_id})
    logger.info("WebSocket client connected and handshake sent", submission_id=submission_id)
    
    redis_client = await get_redis()
    pubsub = redis_client.pubsub()
    channel_name = f"submission_{submission_id}"
    
    try:
        await pubsub.subscribe(channel_name)
        logger.info("Subscribed to Redis channel", channel=channel_name)
        
        async for message in pubsub.listen():
            if message and message["type"] == "message":
                data_str = message["data"]
                try:
                    payload = json.loads(data_str)
                except Exception:
                    payload = {"raw": data_str}
                
                await websocket.send_json(payload)
                
                # Check if final event reached to close stream cleanly
                if isinstance(payload, dict) and payload.get("event") in ("COMPLETED", "FAILED", "AI_REVIEW_COMPLETED"):
                    await websocket.send_json({"event": "STREAM_FINISHED"})
                    break

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected", submission_id=submission_id)
    except Exception as e:
        logger.error("WebSocket streaming error", submission_id=submission_id, error=str(e))
    finally:
        try:
            await pubsub.unsubscribe(channel_name)
            await pubsub.aclose()
        except Exception:
            pass
        logger.info("PubSub unsubscribed and cleaned up", submission_id=submission_id)
