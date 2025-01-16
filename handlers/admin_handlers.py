from enum import Enum, auto

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (CallbackQueryHandler, CommandHandler, ContextTypes,
                          ConversationHandler)

from config import ADMIN_CHAT_ID, USER_DB_CONFIG
from services.service_factory import ServiceFactory

# Состояния разговора


class AdminStates(Enum):
    SHOWING_REQUESTS = auto()


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Отображает меню администратора.

    :param update: Объект обновления
    :param context: Контекст
    :return: Состояние ConversationHandler
    """
    user_service = ServiceFactory.get_user_service(
        USER_DB_CONFIG, ADMIN_CHAT_ID)

    if not user_service.is_admin(update.effective_chat.id):
        await update.message.reply_text("Вы не авторизованы.")
        return ConversationHandler.END

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "Список заявок", callback_data="admin:list_requests")
    ]])
    await update.message.reply_text("Меню администратора:", reply_markup=keyboard)
    return AdminStates.SHOWING_REQUESTS


async def list_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает список заявок с пагинацией.

    :param update: Объект обновления
    :param context: Контекст
    :return: Состояние ConversationHandler
    """
    user_service = ServiceFactory.get_user_service(
        USER_DB_CONFIG, ADMIN_CHAT_ID)
    callback_query = update.callback_query

    if not user_service.is_admin(update.effective_chat.id):
        await update.message.reply_text("Вы не авторизованы.")
        return ConversationHandler.END

    page = context.user_data.get('page', 1)
    page_size = 10
    pending_requests, total_count = user_service.get_pending_users(
        page, page_size)

    if not pending_requests:
        text = "Нет ожидающих заявок."
        await (callback_query.message.edit_text(text) if callback_query
               else update.message.reply_text(text))
        return ConversationHandler.END

    total_pages = (total_count + page_size - 1) // page_size

    buttons = []
    for user_id in pending_requests:
        buttons.extend([
            [InlineKeyboardButton("Профиль", url=f"tg://user?id={user_id}")],
            [
                InlineKeyboardButton(f"Одобрить {user_id}",
                                     callback_data=f"admin:approve:{user_id}"),
                InlineKeyboardButton(f"Отклонить {user_id}",
                                     callback_data=f"admin:reject:{user_id}")
            ]
        ])

    if total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton("◀️ Назад",
                                                    callback_data="admin:prev_page"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("Вперёд ▶️",
                                                    callback_data="admin:next_page"))
        buttons.append(nav_buttons)

    keyboard = InlineKeyboardMarkup(buttons)
    text = f"Ожидающие заявки (Страница {page}/{total_pages}):"

    await (callback_query.message.edit_text(text, reply_markup=keyboard)
           if callback_query else update.message.reply_text(text, reply_markup=keyboard))

    return AdminStates.SHOWING_REQUESTS


async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает админские callback-запросы.

    :param update: Объект обновления
    :param context: Контекст
    :return: Состояние ConversationHandler
    """
    user_service = ServiceFactory.get_user_service(
        USER_DB_CONFIG, ADMIN_CHAT_ID)
    query = update.callback_query
    data = query.data

    if data.startswith("admin:approve:"):
        user_id = int(data.split(":")[2])
        user_service.set_approved(user_id)
        await query.answer("Пользователь одобрен!")

    elif data.startswith("admin:reject:"):
        user_id = int(data.split(":")[2])
        user_service.remove_pending(user_id)
        await query.answer("Пользователь отклонён!")

    elif data in ["admin:prev_page", "admin:next_page"]:
        context.user_data['page'] = (max(1, context.user_data.get('page', 1) - 1)
                                     if data == "admin:prev_page"
                                     else context.user_data.get('page', 1) + 1)
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
