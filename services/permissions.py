from config import ADMIN_CHAT_ID
from services.db import load_data

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_CHAT_ID

def is_approved_user(user_id: int, approved_file: str) -> bool:
    approved_users = load_data(approved_file)
    return user_id in approved_users
