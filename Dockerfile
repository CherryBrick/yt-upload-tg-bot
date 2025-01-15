FROM python:3.12-slim

# Установка рабочих зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    jq ffmpeg curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Установим рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY . .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Указываем команды запуска контейнера
CMD ["python", "main.py"]
