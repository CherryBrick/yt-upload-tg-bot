#!/usr/bin/env bash
source "$HOME/telegram/bin/activate"
set -a
source /path/to/.env
set +a
# Переменные

CHAT_ID="$2"  # Передаётся из бота
URL="$1"

# Проверяем, что URL передан
if [ -z "$URL" ]; then
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_TOKEN/sendMessage" \
        -d chat_id="$CHAT_ID" \
        -d text="Ошибка: Ссылка не передана."
    exit 1
fi

# Получаем метаданные видео
VIDEO_INFO=$(yt-dlp --print-json "$URL" | jq -r '.title, .uploader')
if [ $? -ne 0 ]; then
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_TOKEN/sendMessage" \
        -d chat_id="$CHAT_ID" \
        -d text="Ошибка: Не удалось получить информацию о видео по ссылке $URL."
    exit 1
fi

# Парсим метаданные
TITLE=$(echo "$VIDEO_INFO" | head -n 1)
UPLOADER=$(echo "$VIDEO_INFO" | tail -n 1)

# Уведомляем о начале загрузки
curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_TOKEN/sendMessage" \
    -d chat_id="$CHAT_ID" \
    -d text="Начинаю загрузку: $TITLE от $UPLOADER."

# Загружаем видео
yt-dlp -f "bestvideo+bestaudio/best" -o "$HOME$VIDEOS_DIR/%(title)s.%(ext)s" "$URL"
if [ $? -eq 0 ]; then
    # Уведомляем об успешной загрузке
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_TOKEN/sendMessage" \
        -d chat_id="$CHAT_ID" \
        -d text="Загрузка завершена: $TITLE. Видео добавлено в библиотеку Jellyfin."
else
    # Уведомляем об ошибке загрузки
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_TOKEN/sendMessage" \
        -d chat_id="$CHAT_ID" \
        -d text="Ошибка при загрузке видео: $TITLE."
    exit 1
fi

# Обновляем библиотеку Jellyfin
curl -X POST "$JELLYFIN_API_URL" \
     -H "X-Emby-Token: $JELLYFIN_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"id":"$JELLYFIN_API_MEDIA_ID"}'
