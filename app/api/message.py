from flask import request, current_app
from flask_restful import Resource

from app.services.message_service import MessageService
from app.repositories.message_repository import IdempotencyConflict

class MessageListResource(Resource):
    
    def get(self, room_id):
        service = MessageService(current_app.extensions['redis'])
        raw_after_seq = request.args.get("after_seq", "0")
        
        try:
            after_seq = int(raw_after_seq)
            
            result = service.list_messages(
                room_id=room_id,
                after_seq=after_seq   
            )
            
            return result, 200
        
        except ValueError as err:
            return {"error": str(err)}, 400
        
        except LookupError as err:
            return {"error": str(err)}, 404
        
    def post(self, room_id):
        data = request.get_json(silent=True)
        
        if not isinstance(data, dict):
            return {"error": "A valid JSON object is required"}, 400
        
        idempotency_key = request.headers.get("Idempotency-Key")
        
        service = MessageService(current_app.extensions['redis'])
        
        try:
            message, created = service.send_message(
                room_id=room_id,
                author=data.get("author"),
                content=data.get("content"),
                idempotency_key=idempotency_key
            )
            
            return {"message": message}, 201 if created else 200
        
        except ValueError as err:
            return {"error": str(err)}, 400
        
        except LookupError as err:
            return {"error": str(err)}, 404
        
        except IdempotencyConflict as err:
            return {"error": str(err)}, 422
        
class MessageResource(Resource):

    def delete(self, room_id, message_seq):
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return {"error": "A valid JSON object is required"}, 400

        service = MessageService(current_app.extensions["redis"])

        try:
            message, deleted = service.delete_message(
                room_id=room_id,
                message_seq=message_seq,
                author=data.get("author")
            )
            return {"message": message, "deleted": deleted}, 200

        except ValueError as err:
            return {"error": str(err)}, 400

        except LookupError as err:
            return {"error": str(err)}, 404

        except KeyError as err:
            return {"error": str(err)}, 404

        except PermissionError as err:
            return {"error": str(err)}, 403
            