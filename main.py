import json
import telebot
from telebot import types
import requests
import datetime
import sqlite3

# Токен
TELEGRAM_BOT_TOKEN = "7871033563:AAFZl-L3cad2lmMiURMt5HSgLcpMfrLAotg"

# URL API Facticity
FACTICITY_API_URL = "https://api.facticity.ai"

# API-ключ для Facticity
FACTICITY_API_KEY = "a72e06a5-aba2-40e4-ae14-cc8277a968e3"


print(f"Запрос к API Facticity")
print(f"Base URL: {FACTICITY_API_URL}")
print(f"Полный URL: {FACTICITY_API_URL}")

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


def create_nav_buttons():
    """Создает inline-кнопки навигации"""
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("🔍 Проверить факт", callback_data="fact_check")
    btn2 = types.InlineKeyboardButton("📜 История запросов", callback_data="history")
    markup.row(btn1, btn2)
    return markup


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
    print(f"\n{'='*50}")
    print(f"Время: {timestamp}")
    print(f"User ID: {user.id}")
    print(f"Username: @{user.username}" if user.username else "Username: Не указан")
    print(f"Имя: {user.first_name}" if user.first_name else "Имя: Не указано")
    print(f"Фамилия: {user.last_name}" if user.last_name else "Фамилия: Не указана")
    print(f"Запрос: {query}")
    print(f"{'='*50}\n")


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

        print(f"Запрос к API Facticity")
        print(f"Base URL: {FACTICITY_API_URL}")
        print(f"Полный URL: {FACTICITY_API_URL}fact-check")
        # ПРАВИЛЬНОЕ ФОРМИРОВАНИЕ URL
        url = FACTICITY_API_URL.rstrip('/') + '/fact-check'
        print(f"Отправляю запрос на URL: {url}")
        print(f"Заголовки: {headers}")
        print(f"Данные: {data}")

        response = requests.post(url, json=data, headers=headers, timeout=65)
        print(f"API Response Status: {response.status_code}")

        response.raise_for_status()

        # Парсим ответ
        response_json = response.json()
        print(f"Полный ответ API: {json.dumps(response_json, indent=2, ensure_ascii=False)}")

        # Проверяем наличие ключа
        if 'overall_assessment' in response_json:
            answer = response_json['overall_assessment']
        else:
            answer = f"Ответ API не содержит 'overall_assessment'. Полный ответ: {json.dumps(response_json)}"

        print(f"Извлеченный ответ: {answer}")
        return answer

    except requests.exceptions.Timeout:
        error_msg = "Превышено время ожидания ответа от API (60 секунд)"
        print(f"Timeout Error: {error_msg}")
        return error_msg

    except requests.exceptions.ConnectionError as e:
        error_msg = f"Ошибка подключения к API: {e}"
        print(f"Connection Error: {error_msg}")
        return error_msg

    except requests.exceptions.RequestException as e:
        error_msg = f"Произошла ошибка при проверке факта: {e}"
        print(f"Request Error: {error_msg}")
        return error_msg

    except KeyError as e:
        error_msg = f"Некорректный формат ответа от API: отсутствует ключ {e}"
        print(f"Key Error: {error_msg}")
        return error_msg

    except json.JSONDecodeError as e:
        error_msg = f"Ошибка парсинга JSON ответа: {e}"
        print(f"JSON Error: {error_msg}")
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


# Обработчик inline-кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_inline_buttons(call):
    """Обрабатывает нажатия inline-кнопок"""
    try:
        if call.data == "fact_check":
            # Редактируем сообщение с кнопками, убирая их
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=call.message.text,
                reply_markup=None
            )
            msg = bot.send_message(call.message.chat.id, "Отправьте текст или факт для проверки:")
            bot.register_next_step_handler(msg, process_fact_check)

        elif call.data == "history":
            # call.message вместо call.message.chat.id
            show_history(call.message)

            # Редактируем сообщение с кнопками, добавляя текст
            try:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=call.message.text,
                    reply_markup=None
                )
            except:
                pass  # Если сообщение уже отредактировано

        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Ошибка обработки кнопки: {e}")


def show_history(message):
    """Показывает историю запросов"""
    user = message.from_user
    print_user_request(user, "show history")

    # Отладочная информация
    print(f"Запрашиваю историю для user_id: {user.id}")

    # Проверим, что есть в базе
    cursor.execute("SELECT COUNT(*) FROM user_requests WHERE user_id=?", (user.id,))
    count = cursor.fetchone()[0]
    print(f"Всего записей в БД для user_id {user.id}: {count}")

    history = get_user_history(user.id)
    print(f"Получено записей истории: {len(history)}")

    if not history:
        # Отправляем сообщение с кнопками
        bot.send_message(
            message.chat.id,
            "У вас пока нет истории запросов. Сначала проверьте несколько фактов!",
            reply_markup=create_nav_buttons()
        )
        return

    response = "📜 Ваша история запросов:\n\n"
    for i, (request, response_text, timestamp) in enumerate(history, 1):
        response += f"🔹 Запрос #{i} ({timestamp})\n"
        response += f"❓ {request[:100]}{'...' if len(request) > 100 else ''}\n"
        response += f"📌 Ответ: {response_text[:100]}{'...' if len(response_text) > 100 else ''}\n\n"

    # Отправляем историю с кнопками
    bot.send_message(
        message.chat.id,
        response,
        reply_markup=create_nav_buttons()
    )

# Обработчик команды /fact_check
@bot.message_handler(commands=["fact_check"])
def handle_fact_check(message):
    """Обрабатывает команду /fact-check."""
    print_user_request(message.from_user, "/fact_check command")
    msg = bot.send_message(message.chat.id, "Отправьте текст или факт для проверки:")
    bot.register_next_step_handler(msg, process_fact_check)


# Обработчик команды /history
@bot.message_handler(commands=["history"])
def handle_history(message):
    """Показывает историю запросов пользователя"""
    show_history(message)


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

        # Удаляем сообщение об обработке
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


if __name__ == "__main__":
    print("Бот запущен и готов к работе!")

    # Проверим структуру базы данных
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_requests'")
    if cursor.fetchone():
        print("Таблица user_requests существует")

        # Посчитаем общее количество записей
        cursor.execute("SELECT COUNT(*) FROM user_requests")
        total = cursor.fetchone()[0]
        print(f"Всего записей в базе: {total}")
    else:
        print("Таблица user_requests не найдена!")

    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка в работе бота: {e}")
    finally:
        conn.close()

