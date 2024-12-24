from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from services.permissions import is_admin

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ответ на неизвестную команду."""
    await update.message.reply_text(
        "Неизвестная команда. Напишите /help, чтобы узнать, какие команды доступны."
    )

async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ответ на любое некомандное сообщение."""
    await update.message.reply_text("Я понимаю только команды. Напишите /help, чтобы увидеть список.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    text = "Доступные команды:\n"

    # Общие
    text += "/start — Проверить/получить доступ.\n"
    text += "/menu — Открыть интерактивное меню.\n"

    # Если пользователь админ, добавим админские команды
    if is_admin(user_id):
        text += "\nАдминистраторские команды:\n"
        text += "/list_requests — Показать все заявки.\n"
        text += "/approve <user_id> — Подтвердить заявку.\n"
        text += "/reject <user_id> — Отклонить заявку.\n"

    await update.message.reply_text(text)

