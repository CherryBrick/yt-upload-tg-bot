import os

from services.db import DBConfig

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
JELLYFIN_API_KEY = os.getenv("JELLYFIN_API_KEY")

USER_DB_CONFIG = DBConfig(
    host=os.getenv("POSTGRES_HOST", ''),
    port=os.getenv("POSTGRES_PORT", ''),
    user=os.getenv("POSTGRES_USER", ''),
    password=os.getenv("POSTGRES_PASSWORD", ''),
    database=os.getenv("USER_DB_NAME", ''),
)
