from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from services.db import load_data, save_data
from config import PENDING_REQUESTS_FILE, APPROVED_USERS_FILE
from services.permissions import is_admin


# /list_requests
async def list_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id):
        return

    pending_requests = load_data(PENDING_REQUESTS_FILE)
    if not pending_requests:
        await update.message.reply_text("Нет новых заявок.")
        return

    # Формируем кнопки
    buttons = []
    for uid in pending_requests:
        row = [
            InlineKeyboardButton(
                text=f"Одобрить {uid}", 
                callback_data=f"approve:{uid}"
            ),
            InlineKeyboardButton(
                text=f"Отклонить {uid}",
                callback_data=f"reject:{uid}"
            )
        ]
        buttons.append(row)

    keyboard = InlineKeyboardMarkup(buttons)

    # Отправляем сообщение с кнопками
    await update.message.reply_text("Заявки на доступ:", reply_markup=keyboard)

# /approve <user_id>
async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id):
        return

    args = context.args
    if not args:
        await update.message.reply_text("Использование: /approve <user_id>")
        return

    target_user_id = int(args[0])
    pending_requests = load_data(PENDING_REQUESTS_FILE)
    approved_users = load_data(APPROVED_USERS_FILE)

    if target_user_id not in pending_requests:
        await update.message.reply_text(f"Пользователь {target_user_id} не подавал заявку.")
        return

    # Убираем из pending, добавляем в approved
    pending_requests.remove(target_user_id)
    approved_users.append(target_user_id)

    save_data(PENDING_REQUESTS_FILE, pending_requests)
    save_data(APPROVED_USERS_FILE, approved_users)

    await update.message.reply_text(f"Пользователь {target_user_id} подтверждён.")
    await context.bot.send_message(
        chat_id=target_user_id, 
        text="Ваша заявка на доступ подтверждена! Теперь можете использовать /download."
    )

# /reject <user_id>
async def reject_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id):
        return

    args = context.args
    if not args:
        await update.message.reply_text("Использование: /reject <user_id>")
        return

    target_user_id = int(args[0])
    pending_requests = load_data(PENDING_REQUESTS_FILE)

    if target_user_id not in pending_requests:
        await update.message.reply_text(f"Пользователь {target_user_id} не подавал заявку.")
        return

    pending_requests.remove(target_user_id)
    save_data(PENDING_REQUESTS_FILE, pending_requests)

    await update.message.reply_text(f"Заявка от пользователя {target_user_id} отклонена.")
    await context.bot.send_message(
        chat_id=target_user_id, 
        text="Ваша заявка на доступ отклонена."
    )

# CallbackQueryHandler для InlineKeyboard
async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("Недостаточно прав.")
        return

    data = query.data  # Например, "approve:123456" или "reject:123456"
    action, target_id_str = data.split(":")
    target_id = int(target_id_str)

    pending_requests = load_data(PENDING_REQUESTS_FILE)
    approved_users = load_data(APPROVED_USERS_FILE)

    if action == "approve":
        if target_id in pending_requests:
            pending_requests.remove(target_id)
            approved_users.append(target_id)
            save_data(PENDING_REQUESTS_FILE, pending_requests)
            save_data(APPROVED_USERS_FILE, approved_users)
            await query.answer(f"Пользователь {target_id} подтверждён.")
            await context.bot.send_message(
                chat_id=target_id, 
                text="Ваша заявка подтверждена!"
            )
        else:
            await query.answer(f"Пользователь {target_id} не в списке заявок.")

    elif action == "reject":
        if target_id in pending_requests:
            pending_requests.remove(target_id)
            save_data(PENDING_REQUESTS_FILE, pending_requests)
            await query.answer(f"Пользователь {target_id} отклонён.")
            await context.bot.send_message(
                chat_id=target_id, 
                text="Ваша заявка отклонена."
            )
        else:
            await query.answer(f"Пользователь {target_id} не в списке заявок.")

    # Опционально можно удалить сообщение с кнопками:
    await query.message.delete()
