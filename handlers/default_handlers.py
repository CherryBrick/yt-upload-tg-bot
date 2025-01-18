from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_CHAT_ID, USER_DB_CONFIG
from services.service_factory import ServiceFactory


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle an unrecognized command sent to the Telegram bot.
    
    This function is triggered when a user sends a command that is not defined in the bot's command set. It provides a helpful response guiding the user to use the /help command to discover available bot commands.
    
    Args:
        update (Update): The incoming Telegram update containing message information
        context (ContextTypes.DEFAULT_TYPE): The context for the current bot interaction
    
    Sends a reply message to the user informing them about the unknown command and suggesting they use /help.
    """
    await update.message.reply_text(
        "Неизвестная команда. Напишите /help, чтобы узнать, какие команды доступны."
    )


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Ответ на любое некомандное сообщение.

    :param update: Объект обновления
    :param context: Контекст
    """
    await update.message.reply_text("Я понимаю только команды. Напишите /help, чтобы увидеть список.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /help command, providing a list of available commands based on user permissions.
    
    Parameters:
        update (Update): Telegram update object containing message information
        context (ContextTypes.DEFAULT_TYPE): Context for the current bot interaction
    
    Sends a message to the user with:
        - Basic commands for all users
        - Additional administrative commands for admin users
        - Commands are displayed in Russian language
    
    Notes:
        - Retrieves user service to check admin status
        - Uses user's chat ID to determine command access
        - Dynamically generates command list based on user role
    """
    user_service = ServiceFactory.get_user_service(
        USER_DB_CONFIG, ADMIN_CHAT_ID)
    user_id = update.effective_chat.id

    text = "Доступные команды:\n/start — Проверить/получить доступ.\n"

    if user_service.is_admin(user_id):
        text += "\nАдминистраторские команды:\n"
        text += "/list_requests — Показать все заявки.\n"
        text += "/approve <user_id> — Подтвердить заявку.\n"
        text += "/reject <user_id> — Отклонить заявку.\n"

    await update.message.reply_text(text)
