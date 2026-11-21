from flask import request, current_app
from flask_restful import Resource

from app.services.room_service import RoomService

class RoomsListResource(Resource):
    
    def get(self):
        service = RoomService(current_app.extensions['redis'])
        
        rooms = service.listRooms()
        
        return {"rooms": rooms}, 200
    
    def post(self):
        data = request.get_json(silent=True)
        
        if not isinstance(data, dict):
            return {"Error" : "A valid JSON object is required"}, 400
        
        try:
            service = RoomService(current_app.extensions['redis'])
            room = service.createRoom(data.get("name"))
            
            return {"room": room}, 201
        except ValueError as err:
            return {"Error": str(err)}, 400