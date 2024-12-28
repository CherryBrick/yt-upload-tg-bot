import logging
from telegram.ext import (ApplicationBuilder,
                          CommandHandler, MessageHandler, filters)
from config import BOT_TOKEN
from handlers import admin_handlers, default_handlers, user_handlers

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main() -> None:
    """
    Основная функция для запуска бота.
    """
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
    # main()
    main()
