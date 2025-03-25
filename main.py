import json

import telebot
from telebot import types
import requests

# Токен вашего Telegram бота
TELEGRAM_BOT_TOKEN = "7871033563:AAFZl-L3cad2lmMiURMt5HSgLcpMfrLAotg"

# URL API Facticity
FACTICITY_API_URL = "https://api.facticity.ai/"

# API-ключ для Facticity
FACTICITY_API_KEY = "b48e0da6-bca7-4969-817a-02ff0e3985ff"

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


# Функция для отправки запроса к API Facticity
def get_fact_check(query: str) -> str:
    """
    Отправляет запрос к API Facticity и возвращает ответ.
    """
    try:
        # Заголовки запроса
        headers = {
            "accept": "application/json",
            'X-API-KEY': FACTICITY_API_KEY,
            "Content-Type": "application/json"
            # Используем API-ключ
        }
        # Тело запроса

        data = {
            "query": query,
            "timeout": 60,
            "mode": "sync",
            "version": "v3"
        }  # Предполагаем, что API принимает поле 'query'
        # Отправляем POST-запрос к API Facticity
        print(FACTICITY_API_URL + 'fact-check')
        response = requests.post(FACTICITY_API_URL + 'fact-check', json=data, headers=headers)
        #print(response.)
        response.raise_for_status()  # Проверяем, что запрос успешен

        # Возвращаем ответ от API
        print(response.__dict__)
        return response.json().get("answer", "Не удалось получить ответ от Facticity.")
    except requests.exceptions.RequestException as e:
        return f"Произошла ошибка при проверке факта: {e}"


# Обработчик команды /start
@bot.message_handler(commands=["start", "main"])
def send_welcome(message):
    """
    Обрабатывает команду /start и /main.
    """
    bot.reply_to(
        message,
        "Привет! Я бот для проверки фактов. Используй команду /fact-check, чтобы проверить факт."
    )


# Обработчик команды /fact-check
@bot.message_handler(commands=["fact_check"])
def handle_fact_check(message):
    """
    Обрабатывает команду /fact_check.
    """
    # Запрашиваем у пользователя текст для проверки
    msg = bot.reply_to(message, "Отправьте текст или факт для проверки:")
    bot.register_next_step_handler(msg, process_fact_check)


# Функция для обработки текста от пользователя
def process_fact_check(message):
    """
    Обрабатывает текст от пользователя и отправляет запрос к API Facticity.
    """
    user_query = message.text  # Получаем текст от пользователя
    fact_check_response = get_fact_check(user_query)  # Отправляем запрос к API Facticity
    bot.reply_to(message, fact_check_response)  # Отправляем ответ пользователю


# Запуск бота
if __name__ == "__main__":
    print("Бот запущен")
    bot.polling(none_stop=True)
    main()