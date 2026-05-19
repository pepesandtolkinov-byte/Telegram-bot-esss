FROM python:3.9-slim
WORKDIR /app
RUN pip install --no-cache-dir "aiogram<2.15" "aiohttp<=3.8.5"
COPY . .
CMD ["python", "bot.py"]
