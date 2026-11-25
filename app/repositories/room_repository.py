from redis import Redis
from datetime import datetime, timezone

class RoomRepository:
    
    ROOMS_KEY = "chat:rooms"
    
    def __init__(self, redis_conn: Redis) -> None:
        self._conn =  redis_conn
        
    def _meta_key(self, roomId) -> str:
        return f"chat:rooms:{roomId}:meta"
    
    def createRoom(self, roomName: str):
        roomId = self._conn.incr("chat:rooms:next_id", 1)
        createdAt = datetime.now(timezone.utc).isoformat()
        
        with self._conn.pipeline(transaction=True) as pipe:
            pipe.sadd(self.ROOMS_KEY, roomId)
            
            pipe.hset(
                self._meta_key(roomId),
                mapping={
                    "id": roomId,
                    "name": roomName,
                    "created_at": createdAt
                }
            )
            
            pipe.execute()
        
        return {
            "id": roomId,
            "name": roomName,
            "created_at": createdAt
        }
        
    def getRooms(self):
        roomIds = self._conn.smembers(self.ROOMS_KEY)
        
        if not roomIds:
            return []
        
        with self._conn.pipeline(transaction=False) as pipe:
            for roomId in roomIds:
                pipe.hgetall(self._meta_key(roomId))
            
            rooms = pipe.execute()
            
        return sorted(
            (room for room in rooms if room),
            key=lambda room: (room["created_at"], room["id"])
        )
        
    def getRoom(self, roomId: int):
        room = self._conn.hgetall(self._meta_key(roomId))
        return room if room else None