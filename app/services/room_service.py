import secrets
from app.repositories.room_repository import RoomRepository

class RoomService:
    MAX_NAME_LEN = 80
    
    def __init__(self, redis_client):
        self.repository = RoomRepository(redis_client)
        
    def createRoom(self, name):
        if not isinstance(name, str):
            raise ValueError("Room name must be a string")

        name = name.strip()
        
        if not name:
            raise ValueError("Room name must not be empty")

        if len(name) > self.MAX_NAME_LEN:
            raise ValueError("Room name is too long!")
        
        # roomId = secrets.token_urlsafe(10)
        
        return self.repository.createRoom(name)
    
    def listRooms(self):
        return self.repository.getRooms()