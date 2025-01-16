import logging
import subprocess

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (CallbackQueryHandler, CommandHandler, ContextTypes,
                          ConversationHandler, MessageHandler, filters)

from config import ADMIN_CHAT_ID, USER_DB_CONFIG
from services.service_factory import ServiceFactory

WAITING_FOR_LINK = 1

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду /start.

    :param update: Объект обновления
    :param context: Контекст
    :return: Состояние ConversationHandler
    """
    user_service = ServiceFactory.get_user_service(
        USER_DB_CONFIG, ADMIN_CHAT_ID)
    user_id = update.effective_chat.id

    if user_service.is_approved_user(user_id):
        await user_menu(update, context)
    elif user_service.is_pending_user(user_id):
        await update.message.reply_text("Ваша заявка на рассмотрении у администратора.")
    else:
        user_service.add_user(user_id)
        user_service.set_pending(user_id)
        await update.message.reply_text("Заявка на доступ отправлена администратору.")
    return ConversationHandler.END


async def user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Отображает меню пользователя.

    :param update: Объект обновления
    :param context: Контекст
    :return: Состояние ConversationHandler
    """
    user_service = ServiceFactory.get_user_service(
        USER_DB_CONFIG, ADMIN_CHAT_ID)
    user_id = update.effective_chat.id

    buttons = [[InlineKeyboardButton(
        "Скачать видео" if user_service.is_approved_user(user_id)
        else "Отправить заявку",
        callback_data="user:download" if user_service.is_approved_user(user_id)
        else "user:request_access"
    )]]

    keyboard = InlineKeyboardMarkup(buttons)
    message = await update.message.reply_text("Что вы хотите сделать?",
                                              reply_markup=keyboard)
    context.user_data['message_id'] = message.message_id
    return ConversationHandler.END


async def user_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает callback-запросы пользователя.

    :param update: Объект обновления
    :param context: Контекст
    :return: Состояние ConversationHandler
    """
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if data == "user:request_access":
        await query.message.edit_text("Заявка отправлена...")
        return ConversationHandler.END
    elif data == "user:download":
        await query.message.edit_text(
            "Пришлите ссылку на YouTube обычным сообщением.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Отмена", callback_data="user:cancel")
            ]])
        )
        await query.answer()
        return WAITING_FOR_LINK
    elif data == "user:cancel":
        # Return to main menu
        buttons = [[InlineKeyboardButton(
            "Скачать видео", callback_data="user:download")]]

        keyboard = InlineKeyboardMarkup(buttons)
        await query.message.edit_text("Что вы хотите сделать?", reply_markup=keyboard)
        await query.answer()
        return ConversationHandler.END


async def handle_youtube_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает ссылку на YouTube.

    :param update: Объект обновления
    :param context: Контекст
    :return: Состояние ConversationHandler
    """
    url = update.message.text.strip()
    await update.message.delete()
    try:
        message = await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=context.user_data['message_id'],
            text="Обрабатываю ссылку..."
        )
        return await process_youtube_link(update, context, url)
    except:
        message = await update.message.reply_text("Обрабатываю ссылку...")
        context.user_data['message_id'] = message.message_id
        return await process_youtube_link(update, context, url)


async def process_youtube_link(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> int:
    """
    Обрабатывает ссылку на YouTube и запускает скрипт загрузки.

    :param update: Объект обновления
    :param context: Контекст
    :param url: Ссылка на YouTube
    :return: Состояние ConversationHandler
    """
    user_id = update.effective_chat.id

    if "youtube.com" not in url and "youtu.be" not in url:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=context.user_data['message_id'],
            text="Это не похоже на ссылку YouTube. Попробуйте ещё раз.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Отмена", callback_data="user:cancel")
            ]])
        )
        return WAITING_FOR_LINK

    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=context.user_data['message_id'],
        text=f"Ссылка принята, начинаю загрузку: {url}"
    )

    try:
        subprocess.Popen(
            ['./scripts/download_and_refresh.sh', url, str(user_id)])
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=context.user_data['message_id'],
            text=f"Ошибка при запуске скрипта: {e}"
        )

    return ConversationHandler.END


def get_conversation_handler() -> ConversationHandler:
    """
    Возвращает ConversationHandler для пользователя.

    :return: Объект ConversationHandler
    """
    return ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CallbackQueryHandler(user_callback_handler, pattern='^user:')
        ],
        states={
            WAITING_FOR_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               handle_youtube_link)
            ]
        },
        fallbacks=[
            CommandHandler('start', start),
            CommandHandler('menu', user_menu),
            CommandHandler('help', lambda u, c: ConversationHandler.END),
            CallbackQueryHandler(user_callback_handler, pattern='^user:cancel')
        ]
    )
