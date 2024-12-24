from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.db import load_data, save_data
from config import APPROVED_USERS_FILE, PENDING_REQUESTS_FILE
from services.permissions import is_approved_user
import subprocess

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    pending_requests = load_data(PENDING_REQUESTS_FILE)

    if is_approved_user(user_id, APPROVED_USERS_FILE):
        # await update.message.reply_text("Добро пожаловать! Используйте /help для списка команд.")
        await user_menu(update, context)
    elif user_id in pending_requests:
        await update.message.reply_text("Ваша заявка уже на рассмотрении у администратора.")
    else:
        pending_requests.append(user_id)
        save_data(PENDING_REQUESTS_FILE, pending_requests)
        await update.message.reply_text("Заявка на доступ отправлена администратору.")

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import SCRIPT_PATH  # чтобы не тянуть всё из config сверху
    user_id = update.effective_chat.id

    # Проверяем доступ
    if not is_approved_user(user_id, APPROVED_USERS_FILE):
        await update.message.reply_text("У вас нет доступа. Сначала отправьте заявку командой /start.")
        return

    # Получаем ссылку
    # Можно сделать через /download <url> или просто брать из update.message.text
    if len(context.args) == 0:
        await update.message.reply_text("Пожалуйста, укажите ссылку. Пример: /download https://youtu.be/...")
        return

    url = context.args[0]
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("Это не похоже на ссылку YouTube. Попробуйте ещё раз.")
        return

    await update.message.reply_text("Ссылка принята, начинаю загрузку...")

    try:
        subprocess.Popen([SCRIPT_PATH, url, str(user_id)])
    except Exception as e:
        await update.message.reply_text(f"Ошибка при запуске скрипта: {e}")



async def user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Динамическое меню для пользователя."""
    user_id = update.effective_chat.id

    if is_approved_user(user_id, APPROVED_USERS_FILE):
        # Только кнопка «Скачать видео»
        buttons = [[InlineKeyboardButton("Скачать видео", callback_data="user:download")]]
    else:
        # Только кнопка «Отправить заявку»
        buttons = [[InlineKeyboardButton("Отправить заявку", callback_data="user:request_access")]]

    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Что вы хотите сделать?", reply_markup=keyboard)

async def user_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий Inline-кнопок."""
    query = update.callback_query
    data = query.data  # "user:request_access" или "user:download"
    user_id = query.from_user.id

    if data == "user:request_access":
        # Вызов вашей логики заявки или прямо здесь
        await query.message.reply_text("Заявка отправлена...")
        # Допустим, вы уже делали это в /start, поэтому просто дублирую пример
        # Если нужно — добавьте или вызовите готовую функцию.
    elif data == "user:download":
        # Ставим флаг, что ждём ссылку
        context.user_data["state"] = "waiting_for_link"
        await query.message.reply_text("Пришлите ссылку на YouTube обычным сообщением.")

    await query.answer()

# Теперь отдельный MessageHandler, который отлавливает, когда пользователь в state="waiting_for_link".
# Мы проверяем, действительно ли ссылка похожа на YouTube, и запускаем скачивание.
async def handle_waiting_for_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    url = update.message.text.strip()

    # Проверяем состояние
    if context.user_data.get("state") == "waiting_for_link":
        # Сбрасываем state, чтобы пользователь мог прислать один раз
        context.user_data["state"] = None

        # Проверяем, похоже ли на YouTube
        if "youtube.com" in url or "youtu.be" in url:
            # Здесь можно вызвать вашу функцию скачивания
            await update.message.reply_text(f"Ссылка «{url}» принята, начинаю загрузку...")
            try:
                from config import SCRIPT_PATH
                subprocess.Popen([SCRIPT_PATH, url, str(user_id)])
            except Exception as e:
                await update.message.reply_text(f"Ошибка при запуске скрипта: {e}")
        else:
            await update.message.reply_text("Это не похоже на ссылку YouTube. Попробуйте ещё раз.")
    else:
        # Если пользователь не в режиме ожидания ссылки, игнорируем или отправляем подсказку
        pass
