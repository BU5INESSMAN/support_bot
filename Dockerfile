FROM python:3.11-slim

# Устанавливаем таймзону (важно для логов и планировщика)
ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Запуск модуля
CMD ["python", "-m", "bot.main"]