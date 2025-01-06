from config import ADMIN_CHAT_ID
from services.db import load_data
from typing import List


def is_admin(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь администратором.

    :param user_id: ID пользователя
    :return: True, если пользователь администратор, иначе False
    """
    return user_id == ADMIN_CHAT_ID


def is_approved_user(user_id: int, approved_file: str) -> bool:
    """
    Проверяет, является ли пользователь одобренным.

    :param user_id: ID пользователя
    :param approved_file: Путь к файлу с одобренными пользователями
    :return: True, если пользователь одобрен, иначе False
    """
    approved_users: List[int] = load_data(approved_file)
    return user_id in approved_users
