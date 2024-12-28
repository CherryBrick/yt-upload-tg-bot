import logging
import subprocess
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (ContextTypes, filters, ConversationHandler,
                          CommandHandler, MessageHandler, CallbackQueryHandler)
from config import APPROVED_USERS_FILE, PENDING_REQUESTS_FILE, SCRIPT_PATH
from services.db import load_data, save_data
from services.permissions import is_approved_user

# Define conversation states
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
    user_id = update.effective_chat.id
    pending_requests = load_data(PENDING_REQUESTS_FILE)

    if is_approved_user(user_id, APPROVED_USERS_FILE):
        await user_menu(update, context)
    elif user_id in pending_requests:
        await update.message.reply_text("Ваша заявка уже на рассмотрении у администратора.")
    else:
        pending_requests.append(user_id)
        save_data(PENDING_REQUESTS_FILE, pending_requests)
        await update.message.reply_text("Заявка на доступ отправлена администратору.")
    return ConversationHandler.END


async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду /download.

    :param update: Объект обновления
    :param context: Контекст
    :return: Состояние ConversationHandler
    """
    user_id = update.effective_chat.id

    if not is_approved_user(user_id, APPROVED_USERS_FILE):
        await update.message.reply_text("У вас нет доступа. Сначала отправьте заявку командой /start.")
        return ConversationHandler.END

    if len(context.args) == 0:
        await update.message.reply_text("Пожалуйста, укажите ссылку. Пример: /download https://youtu.be/...")
        return ConversationHandler.END

    url = context.args[0]
    return await process_youtube_link(update, context, url)


async def user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Отображает меню пользователя.

    :param update: Объект обновления
    :param context: Контекст
    :return: Состояние ConversationHandler
    """
    user_id = update.effective_chat.id

    if is_approved_user(user_id, APPROVED_USERS_FILE):
        buttons = [[InlineKeyboardButton(
            "Скачать видео", callback_data="user:download")]]
    else:
        buttons = [[InlineKeyboardButton(
            "Отправить заявку", callback_data="user:request_access")]]

    keyboard = InlineKeyboardMarkup(buttons)
    message = await update.message.reply_text("Что вы хотите сделать?", reply_markup=keyboard)
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
        if is_approved_user(user_id, APPROVED_USERS_FILE):
            buttons = [[InlineKeyboardButton(
                "Скачать видео", callback_data="user:download")]]
        else:
            buttons = [[InlineKeyboardButton(
                "Отправить заявку", callback_data="user:request_access")]]

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
    # Delete user's message with link
    await update.message.delete()
    # Find and edit bot's message
    try:
        message = await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=context.user_data['message_id'],
            text="Обрабатываю ссылку..."
        )
        return await process_youtube_link(update, context, url)
    except:
        # Fallback if message not found
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
        subprocess.Popen([SCRIPT_PATH, url, str(user_id)])
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
            CommandHandler('menu', user_menu),
            CommandHandler('download', download_video),
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
