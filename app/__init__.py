from flask import Flask

from .infrastructure.redis_client import RedisConnectionHandle
from .api import register_routes

def create_app():
    app = Flask(__name__)
    
    app.config['DEBUG'] = True
    
    conn = RedisConnectionHandle()
    app.extensions["redis"] = conn.connect()

    register_routes(app)
        
    return app