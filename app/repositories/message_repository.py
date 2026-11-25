import json
import hashlib

from redis import Redis
from datetime import datetime, timezone

# chat:rooms:{room_id}:message_seq
# chat:rooms:{room_id}:message_order
# chat:rooms:{room_id}:messages

class IdempotencyConflict(Exception):
        pass

class MessageRepository:
    
    HISTORY_LIMIT = 1000
    IDEMPOTENCY_TTL = 86400 # 60*60*24
    
    
    # Cria a mensagem, atualiza o histórico e publica o evento
    # dentro de uma única operação atômica no Redis.
    SEND_MESSAGE_SCRIPT = """
        local existing = redis.call("GET", KEYS[4])
        
        if existing then
            local record = cjson.decode(existing)

            if record.fingerprint ~= ARGV[1] then
                return {-1}
            end
        
            return {1, cjson.encode(record.message)}
        end
        
        local seq = redis.call("INCR", KEYS[1])
        
        local message = {
            id = tonumber(seq),
            seq = tonumber(seq),
            author = ARGV[2],
            content = ARGV[3],
            created_at = ARGV[4],
            deleted = false,
            deleted_at = cjson.null
        }
        
        local message_json = cjson.encode(message)
        
        redis.call("HSET", KEYS[3], tostring(seq), message_json)
        redis.call("RPUSH", KEYS[2], tostring(seq))
        
        while redis.call("LLEN", KEYS[2]) > tonumber(ARGV[6]) do
            local old_seq = redis.call("LPOP", KEYS[2])
            redis.call("HDEL", KEYS[3], old_seq)
        end
        
        local idempotency_record = cjson.encode({
            fingerprint = ARGV[1],
            message = message
        })
        
        redis.call(
            "SET",
            KEYS[4],
            idempotency_record,
            "EX",
            tonumber(ARGV[5])
        )
        
        redis.call(
            "PUBLISH",
            KEYS[5],
            cjson.encode({
                event = "message",
                message_seq = tonumber(seq),
                data = message
            })
        )
        
        return {0, message_json}
    """
    
    # Marca uma mensagem como excluída, sem remover sua posição.
    DELETE_MESSAGE_SCRIPT = """
        local raw = redis.call("HGET", KEYS[1], ARGV[1])

        if not raw then
            return {-1}
        end

        local message = cjson.decode(raw)

        if message.author ~= ARGV[2] then
            return {-2}
        end

        if message.deleted then
            return {1, raw}
        end

        message.deleted = true
        message.deleted_at = ARGV[3]
        message.content = cjson.null

        local updated = cjson.encode(message)

        redis.call("HSET", KEYS[1], ARGV[1], updated)

        redis.call(
            "PUBLISH",
            KEYS[2],
            cjson.encode({
                event = "delete",
                message_seq = tonumber(ARGV[1]),
                data = message
            })
        )

        return {0, updated}
    """
        
    def __init__(self, redis_conn: Redis) -> None:
        self._conn = redis_conn
        self._send_script = self._conn.register_script(self.SEND_MESSAGE_SCRIPT)
        self._delete_script = self._conn.register_script(self.DELETE_MESSAGE_SCRIPT)
        
    #--Redis Keys--
    
    def _seq_key(self, room_id: int) -> str:
        return f"chat:rooms:{room_id}:message_seq"
    
    def _order_key(self, room_id: int) -> str:
        return f"chat:rooms:{room_id}:message_order"
    
    def _messages_key(self, room_id: int) -> str:
        return f"chat:rooms:{room_id}:messages"
    
    def _events_channel(self, room_id: int) -> str:
        return f"chat:rooms:{room_id}:events"
    
    def _idempotency_key(self, room_id: int, key: str) -> str:
        key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return f"chat:rooms:{room_id}:idempotency:{key_hash}"
    
    #--Messages--
    
    def send_message(self, room_id: int, author: str, content: str, idempotency_key: str):
        fingerprint_data = json.dumps(
            {
                "author": author,
                "content": content
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False
        )
        
        fingerprint = hashlib.sha256(fingerprint_data.encode("utf-8")).hexdigest()
        
        created_at = datetime.now(timezone.utc).isoformat()
        
        result = self._send_script(
            keys=[
                self._seq_key(room_id),
                self._order_key(room_id),
                self._messages_key(room_id),
                self._idempotency_key(room_id, idempotency_key),
                self._events_channel(room_id)
            ],
            args=[
                fingerprint,
                author,
                content,
                created_at,
                self.IDEMPOTENCY_TTL,
                self.HISTORY_LIMIT
            ]
        )
        
        status = int(result[0])
        if status == -1:
            raise self.IdempotencyConflict(
                "Idempotency-key already used with a different payload"
            )
            
        message = json.loads(result[1])
        
        return message, status == 0
    
    def get_messages(self, room_id: int, after_seq: int = 0):
        if after_seq < 0:
            raise ValueError("after_seq must be non negative!")
        
        with self._conn.pipeline(transaction=True) as pipe:
            pipe.lrange(self._order_key(room_id), 0, -1)
            pipe.hgetall(self._messages_key(room_id))
            
            sequences, stored_messages = pipe.execute()
            
        messages = []
        
        for seq in sequences:
            if int(seq) <= after_seq:
                continue
            
            raw_message = stored_messages.get(seq)
            if raw_message:
                messages.append(json.loads(raw_message))
                
        oldest_seq = int(sequences[0]) if sequences else None
            
        history_truncated = (
            oldest_seq is not None
            and after_seq < oldest_seq - 1
        )
        
        return {"messages": messages, "history_truncated": history_truncated}
        
    def delete_message(self, room_id: int, message_seq: int, author: str):
        deleted_at = datetime.now(timezone.utc).isoformat()
        
        result = self._delete_script(
            keys=[
                self._messages_key(room_id),
                self._events_channel(room_id)
            ],
            args=[
                str(message_seq),
                author,
                deleted_at
            ]
        )
        
        status = result[0]
        if status == -1:
            raise KeyError("Message not found!")
        
        if status == -2:
            raise PermissionError("Only the author can delete this message!")
        
        message = json.loads(result[1])
        
        return message, status == 0
        
            
    
    
