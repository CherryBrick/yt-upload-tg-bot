import logging
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import BOT_TOKEN
from handlers import user_handlers, admin_handlers, default_handlers

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    # Создаём приложение бота
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # ---------- Хендлеры универсальные ----------
    app.add_handler(CommandHandler("help", default_handlers.help_command))
    
    # ---------- Хендлеры для пользователей ----------
    app.add_handler(CommandHandler("start", user_handlers.start))
    app.add_handler(CommandHandler("download", user_handlers.download_video))
    app.add_handler(CommandHandler("menu", user_handlers.user_menu))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_handlers.handle_waiting_for_link))

    # ---------- Хендлеры для админа ----------
    app.add_handler(CommandHandler("list_requests", admin_handlers.list_requests))
    app.add_handler(CommandHandler("approve", admin_handlers.approve_user))
    app.add_handler(CommandHandler("reject", admin_handlers.reject_user))
    app.add_handler(CallbackQueryHandler(user_handlers.user_callback_handler))

    # ---------- CallbackQueryHandler для InlineKeyboard ----------
    app.add_handler(CallbackQueryHandler(admin_handlers.callback_query_handler))

    # ---------- Обработка некорректных сообщений ----------
    app.add_handler(MessageHandler(filters.COMMAND, default_handlers.unknown_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, default_handlers.unknown_message))

    # Запуск Polling
    app.run_polling()

if __name__ == "__main__":
    main()
