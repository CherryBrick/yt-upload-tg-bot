from services.db import DBConfig
from services.user_service import UserService


class ServiceFactory:
    _user_service = None

    @classmethod
    def get_user_service(cls, db_config: DBConfig, admin_chat_id: int) -> UserService:
        """
        Create and manage a singleton instance of UserService.
        
        This class method ensures that only one instance of UserService is created and reused across the application. If no instance exists, it initializes a new UserService with the provided database configuration and admin chat ID.
        
        Args:
            db_config (DBConfig): Database configuration settings for UserService.
            admin_chat_id (int): Unique identifier for the administrator's chat.
        
        Returns:
            UserService: A singleton instance of UserService, either newly created or previously instantiated.
        """
        if cls._user_service is None:
            cls._user_service = UserService(db_config, admin_chat_id)
        return cls._user_service
