import json
import telebot
from telebot import types
import requests
import datetime
import sqlite3

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

# Словарь для хранения текущей позиции в истории для каждого пользователя
user_history_positions = {}


def save_user_request(user, request_text, response_text):
    """Сохраняет запрос пользователя в базу данных"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO user_requests (user_id, username, first_name, last_name, request_text, response_text, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user.id, user.username, user.first_name, user.last_name, request_text, response_text, timestamp))
    conn.commit()


def get_user_history_count(user_id):
    """Возвращает общее количество запросов пользователя"""
    cursor.execute("SELECT COUNT(*) FROM user_requests WHERE user_id=?", (user_id,))
    return cursor.fetchone()[0]


def get_user_history_page(user_id, offset=0, limit=5):
    """Возвращает страницу истории запросов пользователя"""
    cursor.execute(
        "SELECT request_text, response_text, timestamp FROM user_requests WHERE user_id=? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
        (user_id, limit, offset))
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


def create_history_nav_keyboard(user_id, current_offset, total_count, limit=5):
    """Создает клавиатуру для навигации по истории"""
    keyboard = types.InlineKeyboardMarkup()

    row_buttons = []
    if current_offset > 0:
        row_buttons.append(types.InlineKeyboardButton("⬅ Назад", callback_data=f"history_prev_{current_offset}"))

    if current_offset + limit < total_count:
        row_buttons.append(types.InlineKeyboardButton("Вперед ➡", callback_data=f"history_next_{current_offset}"))

    if row_buttons:
        keyboard.row(*row_buttons)

    keyboard.row(types.InlineKeyboardButton("Закрыть", callback_data="history_close"))
    return keyboard


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
/history - Посмотреть историю ваших запросов (до 100 последних)
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
    """Показывает первую страницу истории запросов пользователя"""
    user = message.from_user
    print_user_request(user, "/history command")

    total_count = get_user_history_count(user.id)
    if total_count == 0:
        bot.reply_to(message, "У вас пока нет истории запросов.")
        return

    # Сохраняем текущую позицию для пользователя
    user_history_positions[user.id] = 0

    history = get_user_history_page(user.id, offset=0)
    response = format_history_response(history, 0, total_count)

    keyboard = create_history_nav_keyboard(user.id, 0, total_count)
    bot.send_message(message.chat.id, response, reply_markup=keyboard)


def format_history_response(history, current_offset, total_count):
    """Форматирует ответ с историей запросов"""
    response = f"📜 Ваша история запросов ({current_offset + 1}-{min(current_offset + 5, total_count)} из {total_count}):\n\n"
    for i, (request, response_text, timestamp) in enumerate(history, 1):
        response += f"🔹 Запрос #{current_offset + i} ({timestamp})\n"
        response += f"❓ {request[:50]}{'...' if len(request) > 50 else ''}\n"
        response += f"📌 Ответ: {response_text[:50]}{'...' if len(response_text) > 50 else ''}\n\n"
    return response


# Обработчик callback-запросов для навигации по истории
@bot.callback_query_handler(func=lambda call: call.data.startswith('history_'))
def handle_history_navigation(call):
    """Обрабатывает навигацию по истории"""
    user_id = call.from_user.id
    data = call.data.split('_')
    action = data[1]
    current_offset = int(data[2]) if len(data) > 2 else 0

    total_count = get_user_history_count(user_id)

    if action == "prev":
        new_offset = max(0, current_offset - 5)
    elif action == "next":
        new_offset = min(total_count - 5, current_offset + 5)
    elif action == "close":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        return

    user_history_positions[user_id] = new_offset
    history = get_user_history_page(user_id, offset=new_offset)
    response = format_history_response(history, new_offset, total_count)

    keyboard = create_history_nav_keyboard(user_id, new_offset, total_count)
    bot.edit_message_text(response, call.message.chat.id, call.message.message_id, reply_markup=keyboard)


# Функция для обработки текста от пользователя
def process_fact_check(message):
    """Обрабатывает текст от пользователя и отправляет запрос к API Facticity."""
    user = message.from_user
    user_query = message.text
    print_user_request(user, user_query)

    # Показываем статус "печатает"
    bot.send_chat_action(message.chat.id, 'typing')

    fact_check_response = get_fact_check(user_query)

    # Сохраняем запрос в историю (но не более 100 последних)
    save_user_request(user, user_query, fact_check_response)

    # Удаляем старые записи, если их больше 100
    cursor.execute(
        "DELETE FROM user_requests WHERE id IN (SELECT id FROM user_requests WHERE user_id=? ORDER BY timestamp ASC LIMIT (SELECT COUNT(*) - 100 FROM user_requests WHERE user_id=?))",
        (user.id, user.id))
    conn.commit()

    bot.reply_to(message, fact_check_response)


if __name__ == "__main__":
    print("Бот запущен и готов к работе!")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка в работе бота: {e}")
    finally:
        conn.close()