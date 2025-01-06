FROM python:3.12-slim

WORKDIR /app

COPY . /app

# Установим необходимые пакеты
RUN apt-get update && apt-get install -y \
    jq \
    ffmpeg \
    curl \
    && apt-get clean

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
