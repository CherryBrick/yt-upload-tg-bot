from services.db import DBConfig
from services.user_service import UserService


class ServiceFactory:
    _user_service = None

    @classmethod
    def get_user_service(cls, db_config: DBConfig, admin_chat_id: int) -> UserService:
        if cls._user_service is None:
            cls._user_service = UserService(db_config, admin_chat_id)
        return cls._user_service
