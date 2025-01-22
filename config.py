import os

from services.db import DBConfig

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_CHAT_ID = int(os.environ["ADMIN_CHAT_ID"])
JELLYFIN_API_KEY = os.environ["JELLYFIN_API_KEY"]

USER_DB_CONFIG = DBConfig(
    host=os.environ["POSTGRES_HOST"],
    port=int(os.environ["POSTGRES_PORT"]),
    user=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
    database=os.environ["USER_DB_NAME"],
)
