from app.repositories.message_repository import MessageRepository
from app.repositories.room_repository import RoomRepository

class MessageService:
    MAX_AUTHOR_LEN = 80
    MAX_CONTENT_LEN = 1000
    
    def __init__(self, redis_client):
        self.message_repository = MessageRepository(redis_client)
        self.room_repository = RoomRepository(redis_client)
    
    #--Validation--
    
    def _validate_room(self, room_id: int):
        if room_id < 0:
            raise ValueError("invalid Room ID")
        
        room = self.room_repository.getRoom(room_id)
        
        if not room:
            raise LookupError("Room not found")
        
    def _validate_author(self, author: str):
        if not isinstance(author, str):
            raise TypeError("Author must be a string")
        
        author = author.strip()
        
        if len(author) > self.MAX_AUTHOR_LEN:
            raise ValueError("Author is too long")
        
        return author
    
    def _validate_content(self, content: str):
        if not isinstance(content, str):
            raise ValueError("Content must be a string")

        content = content.strip()

        if not content:
            raise ValueError("Message content must not be empty")

        if len(content) > self.MAX_CONTENT_LEN:
            raise ValueError("Message content is too long")

        return content
    
    #--Services--
    
    def send_message(self, room_id: int, author: str, content: str, idempotency_key: str):
        self._validate_room(room_id)

        author = self._validate_author(author)
        content = self._validate_content(content)

        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("Idempotency-Key is required")

        if len(idempotency_key) > 200:
            raise ValueError("Idempotency-Key is too long")

        return self.message_repository.send_message(room_id=room_id, author=author, content=content, idempotency_key=idempotency_key)

    
    def list_messages(self, room_id: int, after_seq: int = 0):

        self._validate_room(room_id)

        if after_seq < 0:
            raise ValueError("after_seq must be non-negative")

        return self.message_repository.get_messages(room_id=room_id, after_seq=after_seq)


    def delete_message(self, room_id: int, message_seq: int, author: str):
        self._validate_room(room_id)

        if message_seq <= 0:
            raise ValueError("Invalid message sequence")

        author = self._validate_author(author)

        return self.message_repository.delete_message(room_id=room_id, message_seq=message_seq, author=author)