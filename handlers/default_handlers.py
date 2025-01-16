from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_CHAT_ID, USER_DB_CONFIG
from services.service_factory import ServiceFactory


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Ответ на неизвестную команду.

    :param update: Объект обновления
    :param context: Контекст
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
    Ответ на команду /help.

    :param update: Объект обновления
    :param context: Контекст
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
