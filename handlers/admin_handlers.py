import logging
from enum import Enum, auto
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes
)

from config import APPROVED_USERS_FILE, PENDING_REQUESTS_FILE
from services.db import load_data, save_data
from services.permissions import is_admin

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger()

# Состояния разговора


class AdminStates(Enum):
    SHOWING_REQUESTS = auto()
    HANDLING_APPROVAL = auto()
    HANDLING_REJECTION = auto()

# Точки входа для разговора


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Отображает меню администратора.

    :param update: Объект обновления
    :param context: Контекст
    :return: Состояние ConversationHandler
    """
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text("Вы не авторизованы.")
        return ConversationHandler.END

    buttons = [
        [InlineKeyboardButton(
            "Список заявок", callback_data="admin:list_requests")],
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Меню администратора:", reply_markup=keyboard)
    return AdminStates.SHOWING_REQUESTS


async def list_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает список заявок с пагинацией.

    :param update: Объект обновления
    :param context: Контекст
    :return: Состояние ConversationHandler
    """
    callback_query = update.callback_query

    if not is_admin(update.effective_chat.id):
        await update.message.reply_text("Вы не авторизованы.")
        return ConversationHandler.END

    pending_requests = load_data(PENDING_REQUESTS_FILE)
    if not pending_requests:
        text = "Нет ожидающих заявок."
        if callback_query:
            await callback_query.message.edit_text(text)
        else:
            await update.message.reply_text(text)
        return ConversationHandler.END

    page_size = 10
    page = context.user_data.get('page', 1)
    total_pages = (len(pending_requests) + page_size - 1) // page_size

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    current_requests = pending_requests[start_idx:end_idx]

    buttons = []
    for user_id in current_requests:
        buttons.append([InlineKeyboardButton(
            text="Профиль",
            url=f"tg://user?id={user_id}"
        )])
        buttons.append([
            InlineKeyboardButton(
                f"Одобрить {user_id}", callback_data=f"admin:approve:{user_id}"),
            InlineKeyboardButton(
                f"Отклонить {user_id}", callback_data=f"admin:reject:{user_id}")
        ])

    if total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(
                "◀️ Назад", callback_data="admin:prev_page"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(
                "Вперёд ▶️", callback_data="admin:next_page"))
        buttons.append(nav_buttons)

    keyboard = InlineKeyboardMarkup(buttons)
    text = f"Ожидающие заявки (Страница {page}/{total_pages}):"

    if callback_query:
        await callback_query.message.edit_text(text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text, reply_markup=keyboard)

    return AdminStates.SHOWING_REQUESTS


async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает админские callback-запросы.

    :param update: Объект обновления
    :param context: Контекст
    :return: Состояние ConversationHandler
    """
    query = update.callback_query
    data = query.data

    if data.startswith("admin:approve:"):
        user_id = int(data.split(":")[2])
        approved_users = load_data(APPROVED_USERS_FILE)
        pending_requests = load_data(PENDING_REQUESTS_FILE)

        if user_id not in approved_users:
            approved_users.append(user_id)
            save_data(APPROVED_USERS_FILE, approved_users)

        if user_id in pending_requests:
            pending_requests.remove(user_id)
            save_data(PENDING_REQUESTS_FILE, pending_requests)

        await query.answer("Пользователь одобрен!")
        await list_requests(update, context)

    elif data.startswith("admin:reject:"):
        user_id = int(data.split(":")[2])
        pending_requests = load_data(PENDING_REQUESTS_FILE)

        if user_id in pending_requests:
            pending_requests.remove(user_id)
            save_data(PENDING_REQUESTS_FILE, pending_requests)

        await query.answer("Пользователь отклонён!")
        await list_requests(update, context)

    elif data == "admin:prev_page":
        context.user_data['page'] = max(
            1, context.user_data.get('page', 1) - 1)
        await query.answer()
        await list_requests(update, context)

    elif data == "admin:next_page":
        context.user_data['page'] = context.user_data.get('page', 1) + 1
        await query.answer()
        await list_requests(update, context)

    return AdminStates.SHOWING_REQUESTS


def get_admin_conversation_handler() -> ConversationHandler:
    """
    Возвращает ConversationHandler для админских команд.

    :return: ConversationHandler
    """
    return ConversationHandler(
        entry_points=[
            CommandHandler('admin', admin_menu),
            CommandHandler('list_requests', list_requests),
        ],
        states={
            AdminStates.SHOWING_REQUESTS: [
                CallbackQueryHandler(
                    admin_callback_handler, pattern="^admin:"),
            ],
        },
        fallbacks=[],
    )
