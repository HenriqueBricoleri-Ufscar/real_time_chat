import os
from redis import Redis
from dotenv import load_dotenv

load_dotenv()

class RedisConnectionHandle:
    def __init__(self) -> None:
        self.__host = os.getenv("HOST")
        self.__port = os.getenv("PORT")
        self.__db   = os.getenv("DB")
        self.__connection = None
    
    def connect(self) -> Redis:
        if(self.__connection == None):
            self.__connection = Redis(
                host=self.__host,
                port=self.__port,
                db=self.__db,
                decode_responses=True

            )
        return self.__connection