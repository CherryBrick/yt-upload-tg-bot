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
    Displays the admin menu and provides access to administrative functions.
    
    This function checks the user's admin status and presents an administrative interface with options to view pending requests. If the user is not authorized, access is denied.
    
    Args:
        update (Update): Incoming Telegram update containing user and message information
        context (ContextTypes.DEFAULT_TYPE): Conversation context for the Telegram bot
    
    Returns:
        int: The conversation state (AdminStates.SHOWING_REQUESTS) or ends the conversation if unauthorized
    
    Raises:
        No explicit exceptions raised, but handles unauthorized access by ending the conversation
    """
    user_service = ServiceFactory.get_user_service(
        USER_DB_CONFIG, ADMIN_CHAT_ID)

    if not user_service.is_admin(update.effective_user.id):
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
    Handles the display of pending user requests with pagination.
    
    Checks admin authorization and retrieves pending user requests. Generates an interactive inline keyboard with user profiles, approval/rejection buttons, and navigation controls.
    
    Parameters:
        update (Update): Telegram update object containing user interaction details
        context (ContextTypes.DEFAULT_TYPE): Conversation context for maintaining state
    
    Returns:
        int: The current conversation state (SHOWING_REQUESTS or END)
    
    Raises:
        Sends an unauthorized message if the user is not an admin
        Sends a message indicating no pending requests if the list is empty
    
    Notes:
        - Supports pagination with configurable page size (default 10)
        - Provides direct profile links and action buttons for each pending request
        - Calculates total pages based on request count
        - Adds navigation buttons for multi-page scenarios
    """
    user_service = ServiceFactory.get_user_service(
        USER_DB_CONFIG, ADMIN_CHAT_ID)
    callback_query = update.callback_query

    if not user_service.is_admin(update.effective_user.id):
        await update.message.reply_text("Вы не авторизованы.")
        return ConversationHandler.END

    page = context.user_data.get('page', 1)
    page_size = 10
    pending_requests, total_count = user_service.get_pending_users(
        page, page_size)

    if not pending_requests:
        text = "Нет ожидающих заявок."
        if callback_query:
            await callback_query.message.edit_text(text, reply_markup=keyboard)
        else:
            await update.message.reply_text(text, reply_markup=keyboard)
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
    Handles administrative callback queries for user management and pagination.
    
    This function processes callback queries from the admin interface, supporting:
    - Approving pending users
    - Rejecting pending users
    - Navigating through pages of pending requests
    
    Parameters:
        update (Update): The incoming update from Telegram
        context (ContextTypes.DEFAULT_TYPE): The context for the current conversation
    
    Returns:
        int: The current conversation state (SHOWING_REQUESTS)
    
    Raises:
        ValueError: If callback data is malformed
        TypeError: If user ID cannot be parsed
    
    Side Effects:
        - Modifies user approval status in the user service
        - Updates pagination context
        - Sends callback query answers to the user
        - Refreshes the list of pending requests
    """
    def parse_callback_data(data: str) -> tuple[str, int]:
        """Safely parse callback data and validate user_id."""
        try:
            action, user_id_str = data.split(":", 2)[1:]
            user_id = int(user_id_str)
            if user_id <= 0:
                raise ValueError("Invalid user_id")
            return action, user_id
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid callback data: {e}")


    user_service = ServiceFactory.get_user_service(
        USER_DB_CONFIG, ADMIN_CHAT_ID)
    query = update.callback_query
    data = query.data

    if data.startswith("admin:approve:"):
        _, user_id = parse_callback_data(data)
        user_service.set_approved(user_id)
        await query.answer("Пользователь одобрен!")

    elif data.startswith("admin:reject:"):
        _, user_id = parse_callback_data(data)
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
    Returns a ConversationHandler configured for admin-related commands and interactions.
    
    This handler manages the conversation flow for administrative tasks in the Telegram bot, including:
    - Entry points for admin menu and listing requests
    - State management for displaying and processing user requests
    - Callback query handling for admin actions
    
    Returns:
        ConversationHandler: Configured conversation handler for admin interactions
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
