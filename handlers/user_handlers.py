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
    Handles the /start command for user interaction with the Telegram bot.
    
    Manages user access by checking their approval status and performing appropriate actions:
    - If the user is approved, displays the user menu
    - If the user is already pending, informs them about the pending status
    - If the user is new, adds them to the system and sets their status to pending
    
    Parameters:
        update (Update): Telegram update object containing user and message information
        context (ContextTypes.DEFAULT_TYPE): Telegram context for handling the update
    
    Returns:
        int: Conversation state (ConversationHandler.END)
    
    Raises:
        No explicit exceptions are raised within this method
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
    Displays the user menu with dynamic options based on user approval status.
    
    Parameters:
        update (Update): The incoming Telegram update object
        context (ContextTypes.DEFAULT_TYPE): The context for handling the conversation
    
    Returns:
        int: The conversation state (ConversationHandler.END)
    
    This function creates an inline keyboard with a button that changes dynamically:
    - For approved users: "Скачать видео" (Download video) button
    - For non-approved users: "Отправить заявку" (Send request) button
    
    The function uses the user service to determine the user's approval status and sets 
    the appropriate callback data for the button. It also stores the message ID in the 
    user's context data for potential future reference.
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
    Handles user callback queries for the Telegram bot.
    
    This function processes inline keyboard button interactions, managing different user actions such as requesting access, initiating video download, or canceling an operation.
    
    Parameters:
        update (Update): The incoming update from Telegram containing the callback query
        context (ContextTypes.DEFAULT_TYPE): The context for handling the update
    
    Returns:
        int: The next conversation state for the ConversationHandler
    
    States:
        - If "request_access": Sends a request access message and ends the conversation
        - If "download": Prompts the user to send a YouTube link and moves to WAITING_FOR_LINK state
        - If "cancel": Returns to the main menu and ends the conversation
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
    Handles a YouTube link submitted by the user.
    
    Processes the provided YouTube URL by first deleting the original message and then updating or sending a processing message. Initiates the video download process by calling `process_youtube_link`.
    
    Args:
        update (Update): The incoming Telegram update containing the user's message.
        context (ContextTypes.DEFAULT_TYPE): The context for the current conversation.
    
    Returns:
        int: The conversation state for the ConversationHandler.
    
    Raises:
        Exception: If there are issues editing or sending the processing message.
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
    Process a YouTube video download link and initiate the download script.
    
    This function validates the provided URL, confirms it is a YouTube link, and triggers a download process for the specified video. It handles user interaction by updating messages and managing the conversation state.
    
    Args:
        update (Update): The Telegram update object containing user interaction details.
        context (ContextTypes.DEFAULT_TYPE): The context for the current bot interaction.
        url (str): The YouTube video URL to be downloaded.
    
    Returns:
        int: The next state of the ConversationHandler, either continuing to wait for a link or ending the conversation.
    
    Raises:
        Exception: If there is an error launching the download script.
    
    Notes:
        - Checks if the URL contains YouTube domain variations
        - Provides user feedback during the download process
        - Uses a subprocess to run an external download script
        - Handles potential script execution errors
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
    Returns a ConversationHandler for managing user interactions in the Telegram bot.
    
    This handler defines the conversation flow for user interactions, including:
    - Entry points for starting the bot or handling user callbacks
    - State management for waiting for a YouTube link
    - Fallback commands for navigation and conversation termination
    
    Returns:
        ConversationHandler: Configured conversation handler with defined states and transitions
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
