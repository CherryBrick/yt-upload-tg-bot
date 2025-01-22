import logging
from datetime import datetime as dt

from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler,
                          filters)

from config import ADMIN_CHAT_ID, BOT_TOKEN, USER_DB_CONFIG
from handlers import admin_handlers, default_handlers, user_handlers
from services.service_factory import ServiceFactory

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main() -> None:
    """
    Initializes and starts the Telegram bot application with user, admin, and default handlers.
    
    This function sets up the bot by:
    - Creating a user service using configuration parameters
    - Building the Telegram application with the bot token
    - Adding conversation handlers for help, user interactions, and admin functions
    - Configuring handlers for unknown commands and messages
    - Starting the bot's polling mechanism to receive updates
    
    Parameters:
        None
    
    Returns:
        None
    
    Raises:
        Exception: Potential exceptions during bot initialization or polling
    """

    # Инициализация сервисов
    user_service = ServiceFactory.get_user_service(USER_DB_CONFIG, ADMIN_CHAT_ID)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # ---------- Хендлеры универсальные ----------
    app.add_handler(CommandHandler("help", default_handlers.help_command))

    # ---------- Хендлеры для пользователей ----------
    app.add_handler(user_handlers.get_conversation_handler())

    # ---------- Хендлеры для админа ----------
    app.add_handler(admin_handlers.get_admin_conversation_handler())

    # ---------- Обработка некорректных сообщений ----------
    app.add_handler(MessageHandler(filters.COMMAND,
                    default_handlers.unknown_command))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, default_handlers.unknown_message))

    # Запуск Polling
    app.run_polling()


if __name__ == "__main__":
    main()
