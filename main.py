import json
import telebot
from telebot import types
import requests
import datetime
import sqlite3
from contextlib import closing

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

def init_db():
    """Инициализирует и проверяет базу данных"""
    with closing(sqlite3.connect('user_requests.db', check_same_thread=False)) as conn:
        with conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS user_requests
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          user_id INTEGER NOT NULL,
                          username TEXT,
                          first_name TEXT,
                          last_name TEXT,
                          request_text TEXT NOT NULL,
                          response_text TEXT NOT NULL,
                          timestamp DATETIME NOT NULL)''')
            # Добавляем индекс для ускорения поиска по user_id
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON user_requests(user_id)")
        print("База данных инициализирована")
init_db()

def create_nav_buttons():
    """Создает inline-кнопки навигации"""
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("🔍 Проверить факт", callback_data="fact_check")
    btn2 = types.InlineKeyboardButton("📜 История запросов", callback_data="history")
    markup.row(btn1, btn2)
    return markup


def save_user_request(user, request_text, response_text):
    """Сохраняет запрос пользователя в базу данных"""
    print(f"Сохранение запроса: user_id={user.id}, request='{request_text[:20]}...'")
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with closing(sqlite3.connect('user_requests.db', check_same_thread=False)) as conn:
            with conn:
                conn.execute(
                    "INSERT INTO user_requests (user_id, username, first_name, last_name, request_text, response_text, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user.id, user.username, user.first_name, user.last_name, request_text, response_text, timestamp))
        print(f"Запрос успешно сохранен для user_id: {user.id}")
        return True
    except Exception as e:
        print(f"Ошибка при сохранении запроса: {e}")
        return False


def get_user_history(user_id, limit=5):
    """Возвращает историю запросов пользователя"""
    try:
        with closing(sqlite3.connect('user_requests.db', check_same_thread=False)) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT request_text, response_text, timestamp FROM user_requests WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
                    (user_id, limit))
                history = cursor.fetchall()
                print(f"Получено {len(history)} записей истории для user_id {user_id}")
                return history
    except Exception as e:
        print(f"Ошибка при получении истории: {e}")
        return []


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

Выберите действие:
"""
    # Отправляем сообщение с кнопками
    bot.send_message(message.chat.id, welcome_text, reply_markup=create_nav_buttons())
# Функция для обработки текста от пользователя
def process_fact_check(message):
    """Обрабатывает текст от пользователя и отправляет запрос к API Facticity."""
    try:
        user = message.from_user
        user_query = message.text
        print_user_request(user, user_query)

        # Показываем статус "печатает"
        bot.send_chat_action(message.chat.id, 'typing')

        # Отправляем сообщение о обработке
        processing_msg = bot.send_message(message.chat.id, "◌ Подождите, идёт обработка запроса...")

        fact_check_response = get_fact_check(user_query)

        # Сохраняем запрос в историю
        save_user_request(user, user_query, fact_check_response)

        # Удаляем сообщение о обработке
        bot.delete_message(message.chat.id, processing_msg.message_id)

        # Отправляем ответ с кнопками
        bot.send_message(
            message.chat.id,
            fact_check_response,
            reply_markup=create_nav_buttons()
        )

    except Exception as e:
        # Отправляем сообщение об ошибке с кнопками
        bot.send_message(
            message.chat.id,
            f"Произошла ошибка: {str(e)}",
            reply_markup=create_nav_buttons()
        )
@bot.message_handler(commands=["fact_check"])
def handle_fact_check_command(message):
    """Обрабатывает команду /fact_check"""
    print_user_request(message.from_user, "/fact_check command")
    msg = bot.send_message(message.chat.id, "Отправьте текст или факт для проверки:")
    bot.register_next_step_handler(msg, process_fact_check)

# Обработчик inline-кнопки "Проверить факт" (добавлен)
@bot.callback_query_handler(func=lambda call: call.data == "fact_check")
def handle_fact_check_callback(call):
    try:
        # Редактируем сообщение с кнопками, убирая их
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text,
            reply_markup=None
        )
        msg = bot.send_message(call.message.chat.id, "Отправьте текст или факт для проверки:")
        bot.register_next_step_handler(msg, process_fact_check)
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Ошибка обработки кнопки проверки факта: {e}")

# Обработчик inline-кнопки "Проверить факт"
@bot.callback_query_handler(func=lambda call: call.data == "history")
def handle_history_callback(call):
    try:
        # Редактируем сообщение с кнопками, убирая их
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text,
            reply_markup=None
        )
        show_history(call)  # Передаем сам callback
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Ошибка обработки кнопки истории: {e}")

# Обработчик команды /history
@bot.message_handler(commands=["history"])
def handle_fact_check(message):
    """Обрабатывает команду /fact-check."""
    print_user_request(message.from_user, "/fact_check command")
    msg = bot.send_message(message.chat.id, "Отправьте текст или факт для проверки:")
    bot.register_next_step_handler(msg, process_fact_check)
def show_history(message_or_call):
    """Показывает историю запросов (работает и с сообщениями, и с callback)"""
    # Определяем user_id в зависимости от типа входящего объекта
    if isinstance(message_or_call, types.Message):
        user = message_or_call.from_user
        chat_id = message_or_call.chat.id
    else:  # Это callback
        user = message_or_call.from_user
        chat_id = message_or_call.message.chat.id

    print_user_request(user, "show history")

    history = get_user_history(user.id)  # Используем user.id, а не chat_id

    if not history:
        bot.send_message(
            chat_id,
            "📭 У вас пока нет сохраненных запросов.\n"
            "После проверки фактов они будут отображаться здесь.",
            reply_markup=create_nav_buttons()
        )
        return

    response = ["📜 <b>Ваша история запросов:</b>\n"]
    for i, (request, response_text, timestamp) in enumerate(history, 1):
        dt = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        formatted_time = dt.strftime("%d.%m.%Y в %H:%M")

        response.append(
            f"\n🔹 <b>Запрос #{i}</b> (<i>{formatted_time}</i>)\n"
            f"┣ <b>Факт:</b> {request[:200]}{'...' if len(request) > 200 else ''}\n"
            f"┗ <b>Результат:</b> {response_text[:200]}{'...' if len(response_text) > 200 else ''}"
        )

    bot.send_message(
        chat_id,
        "\n".join(response),
        parse_mode='HTML',
        reply_markup=create_nav_buttons()
    )

# Обработчик команды /history (исправлено)
@bot.message_handler(commands=["history"])
def handle_history_command(message):
    """Обрабатывает команду /history"""
    show_history(message)



if __name__ == "__main__":
    print("Бот запущен и готов к работе!")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка в работе бота: {e}")
    finally:
        conn.close()