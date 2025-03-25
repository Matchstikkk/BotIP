import json
import telebot
from telebot import types
import requests
import datetime
import sqlite3
from collections import deque

# Токен
TELEGRAM_BOT_TOKEN = "7871033563:AAFZl-L3cad2lmMiURMt5HSgLcpMfrLAotg"

# URL API Facticity
FACTICITY_API_URL = "https://api.facticity.ai/"

# API-ключ для Facticity
FACTICITY_API_KEY = "b48e0da6-bca7-4969-817a-02ff0e3985ff"

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Инициализация базы данных SQLite
conn = sqlite3.connect('user_requests.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы для хранения истории запросов
cursor.execute('''CREATE TABLE IF NOT EXISTS user_requests
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              username TEXT,
              first_name TEXT,
              last_name TEXT,
              request_text TEXT,
              response_text TEXT,
              timestamp DATETIME)''')
conn.commit()


def save_user_request(user, request_text, response_text):
    """Сохраняет запрос пользователя в базу данных"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO user_requests (user_id, username, first_name, last_name, request_text, response_text, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user.id, user.username, user.first_name, user.last_name, request_text, response_text, timestamp))
    conn.commit()


def get_user_history(user_id, limit=5):
    """Возвращает историю запросов пользователя"""
    cursor.execute(
        "SELECT request_text, response_text, timestamp FROM user_requests WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
        (user_id, limit))
    return cursor.fetchall()


def print_user_request(user, query):
    """Выводит информацию о запросе пользователя в терминал"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n=== Новый запрос ===")
    print(f"Время: {timestamp}")
    print(f"User ID: {user.id}")
    print(f"Username: @{user.username}" if user.username else "Username: Не указан")
    print(f"Имя: {user.first_name}" if user.first_name else "Имя: Не указано")
    print(f"Фамилия: {user.last_name}" if user.last_name else "Фамилия: Не указана")
    print(f"Запрос: {query}")
    print("===================\n")


# Функция для отправки запроса к API Facticity
def get_fact_check(query: str) -> str:
    """Отправляет запрос к API Facticity и возвращает ответ."""
    try:
        headers = {
            "accept": "application/json",
            'X-API-KEY': FACTICITY_API_KEY,
            "Content-Type": "application/json"
        }

        data = {
            "query": query,
            "timeout": 60,
            "mode": "sync",
            "version": "v3"
        }

        response = requests.post(FACTICITY_API_URL + 'fact-check', json=data, headers=headers)
        print(f"API Response Status: {response.status_code}")

        response.raise_for_status()
        answer = json.loads(response.text)['overall_assessment']
        print(f"API Response: {answer}")
        return answer
    except requests.exceptions.RequestException as e:
        error_msg = f"Произошла ошибка при проверке факта: {e}"
        print(f"API Error: {error_msg}")
        return error_msg


# Обработчик команды /start
@bot.message_handler(commands=["start", "main"])
def send_welcome(message):
    """Обрабатывает команду /start и /main."""
    print_user_request(message.from_user, "/start command")
    welcome_text = """
Привет! Я бот для проверки фактов. 

Доступные команды:
/fact_check - Проверить факт
/history - Посмотреть историю ваших запросов (последние 5)
    """
    bot.reply_to(message, welcome_text)


# Обработчик команды /fact_check
@bot.message_handler(commands=["fact_check"])
def handle_fact_check(message):
    """Обрабатывает команду /fact-check."""
    print_user_request(message.from_user, "/fact_check command")
    msg = bot.reply_to(message, "Отправьте текст или факт для проверки:")
    bot.register_next_step_handler(msg, process_fact_check)


# Обработчик команды /history
@bot.message_handler(commands=["history"])
def handle_history(message):
    """Показывает историю запросов пользователя"""
    user = message.from_user
    print_user_request(user, "/history command")

    history = get_user_history(user.id)

    if not history:
        bot.reply_to(message, "У вас пока нет истории запросов.")
        return

    response = "📜 Ваша история запросов:\n\n"
    for i, (request, response_text, timestamp) in enumerate(history, 1):
        response += f"🔹 Запрос #{i} ({timestamp})\n"
        response += f"❓ {request[:50]}{'...' if len(request) > 50 else ''}\n"
        response += f"📌 Ответ: {response_text[:50]}{'...' if len(response_text) > 50 else ''}\n\n"

    bot.reply_to(message, response)


# Функция для обработки текста от пользователя
def process_fact_check(message):
    """Обрабатывает текст от пользователя и отправляет запрос к API Facticity."""
    user = message.from_user
    user_query = message.text
    print_user_request(user, user_query)

    # Показываем статус "печатает"
    bot.send_chat_action(message.chat.id, 'typing')

    fact_check_response = get_fact_check(user_query)

    # Сохраняем запрос в историю
    save_user_request(user, user_query, fact_check_response)

    bot.reply_to(message, fact_check_response)


if __name__ == "__main__":
    print("Бот запущен и готов к работе!")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка в работе бота: {e}")
    finally:
        conn.close()