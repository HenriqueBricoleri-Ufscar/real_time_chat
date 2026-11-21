from flask_restful import Api
from .room import RoomsListResource

def register_routes(app):
    api = Api(app)
    
    api.add_resource(
        RoomsListResource,
        "/rooms"
    )