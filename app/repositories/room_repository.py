from redis import Redis
from datetime import datetime, timezone

class RoomRepository:
    
    ROOMS_KEY = "chat:rooms"
    
    def __init__(self, redis_conn: Redis) -> None:
        self.__conn =  redis_conn
        
    def _meta_key(self, roomId) -> str:
        return f"chat:rooms:{roomId}:meta"
    
    def createRoom(self, roomName: str):
        roomId = self.__conn.incr("chat:rooms:next_id")
        createdAt = datetime.now(timezone.utc).isoformat()
        
        with self.__conn.pipeline(transaction=True) as pipe:
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
        roomIds = self.__conn.smembers(self.ROOMS_KEY)
        
        if not roomIds:
            return []
        
        with self.__conn.pipeline(transaction=False) as pipe:
            for roomId in roomIds:
                print(roomId)
                pipe.hgetall(self._meta_key(roomId))
            
            rooms = pipe.execute()
            
        return sorted(
            (room for room in rooms if room),
            key=lambda room: (room["created_at"], room["id"])
        )