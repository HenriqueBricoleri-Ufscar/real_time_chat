from flask_restful import Api
from .room import RoomsListResource

from .message import MessageListResource, MessageResource

def register_routes(app):
    api = Api(app)
    
    api.add_resource(
        RoomsListResource,
        "/rooms"
    )
    
    api.add_resource(
        MessageListResource,
        "/rooms/<int:room_id>/messages"
    )
    
    api.add_resource(
        MessageResource,
        "/rooms/<int:room_id>/messages/<int:message_seq>"
    )