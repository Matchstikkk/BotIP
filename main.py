import json
import telebot
from telebot import types
import requests
import datetime
import sqlite3
import html

# Токен
TELEGRAM_BOT_TOKEN = "7871033563:AAFZl-L3cad2lmMiURMt5HSgLcpMfrLAotg"

# URL API Facticity
FACTICITY_API_URL = "https://api.facticity.ai"

# API-ключ для Facticity
FACTICITY_API_KEY = "a72e06a5-aba2-40e4-ae14-cc8277a968e3"

print(f"Запрос к API Facticity")
print(f"Base URL: {FACTICITY_API_URL}")

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Инициализация базы данных SQLite
conn = sqlite3.connect('user_requests.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы для хранения истории запросов с проверкой существования колонок
def init_database():
    """Инициализирует базу данных с нужной структурой"""
    # Сначала создаем таблицу, если она не существует
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_requests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  username TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  request_text TEXT,
                  response_text TEXT,
                  timestamp DATETIME)''')

    # Проверяем существование колонки detailed_response
    cursor.execute("PRAGMA table_info(user_requests)")
    columns = [column[1] for column in cursor.fetchall()]

    # Добавляем колонку detailed_response, если она не существует
    if 'detailed_response' not in columns:
        print("Добавляю колонку detailed_response в таблицу user_requests")
        cursor.execute("ALTER TABLE user_requests ADD COLUMN detailed_response TEXT")

    conn.commit()

# Инициализируем базу данных
init_database()


def create_nav_buttons():
    """Создает inline-кнопки навигации"""
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("🔍 Проверить факт", callback_data="fact_check")
    btn2 = types.InlineKeyboardButton("📜 История запросов", callback_data="history")
    markup.row(btn1, btn2)
    return markup


def create_detail_button(request_id):
    """Создает кнопку 'Подробнее' для конкретного запроса"""
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("📋 Подробнее", callback_data=f"details_{request_id}")
    markup.add(btn)
    return markup


def save_user_request(user, request_text, response_text, detailed_response=None):
    """Сохраняет запрос пользователя в базу данных"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Проверяем, есть ли колонка detailed_response
    cursor.execute("PRAGMA table_info(user_requests)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'detailed_response' in columns:
        cursor.execute(
            """INSERT INTO user_requests 
            (user_id, username, first_name, last_name, request_text, response_text, detailed_response, timestamp) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user.id, user.username, user.first_name, user.last_name,
             request_text, response_text, detailed_response, timestamp))
    else:
        # Если колонки нет, сохраняем без нее
        cursor.execute(
            """INSERT INTO user_requests 
            (user_id, username, first_name, last_name, request_text, response_text, timestamp) 
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user.id, user.username, user.first_name, user.last_name,
             request_text, response_text, timestamp))

    conn.commit()
    return cursor.lastrowid  # Возвращаем ID сохраненного запроса


def get_user_history(user_id, limit=5):
    """Возвращает историю запросов пользователя"""
    cursor.execute(
        "SELECT id, request_text, response_text, timestamp FROM user_requests WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
        (user_id, limit))
    return cursor.fetchall()


def get_request_details(request_id):
    """Возвращает детальную информацию о запросе"""
    cursor.execute(
        "SELECT request_text, response_text, detailed_response, timestamp FROM user_requests WHERE id=?",
        (request_id,))
    return cursor.fetchone()


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
def get_fact_check(query: str):
    """Отправляет запрос к API Facticity и возвращает структурированный ответ."""
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
        url = FACTICITY_API_URL.rstrip('/') + '/fact-check'
        print(f"Отправляю запрос на URL: {url}")

        response = requests.post(url, json=data, headers=headers, timeout=65)
        print(f"API Response Status: {response.status_code}")

        response.raise_for_status()

        # Парсим ответ
        response_json = response.json()
        print(f"Полный ответ API: {json.dumps(response_json, indent=2, ensure_ascii=False)}")

        # Извлекаем данные из ответа
        result = {
            'verdict': 'Неизвестно',
            'explanation': 'Нет объяснения',
            'sources': [],
            'full_response': json.dumps(response_json, ensure_ascii=False, indent=2)
        }

        # Извлекаем вердикт
        if 'overall_assessment' in response_json:
            result['verdict'] = response_json['overall_assessment']

        # Извлекаем объяснение (если есть)
        if 'reasoning' in response_json:
            result['explanation'] = response_json['reasoning']
        elif 'explanation' in response_json:
            result['explanation'] = response_json['explanation']

        # Извлекаем источники (если есть)
        if 'sources' in response_json and isinstance(response_json['sources'], list):
            result['sources'] = response_json['sources']

        print(f"Структурированный результат: {result}")
        return result

    except requests.exceptions.Timeout:
        error_msg = "Превышено время ожидания ответа от API (60 секунд)"
        print(f"Timeout Error: {error_msg}")
        return {
            'verdict': 'Ошибка',
            'explanation': error_msg,
            'sources': [],
            'full_response': error_msg
        }

    except Exception as e:
        error_msg = f"Произошла ошибка при проверке факта: {str(e)}"
        print(f"Error: {error_msg}")
        return {
            'verdict': 'Ошибка',
            'explanation': error_msg,
            'sources': [],
            'full_response': error_msg
        }


def format_verdict_message(verdict, query):
    """Форматирует сообщение с вердиктом"""
    # Определяем эмодзи и текст в зависимости от вердикта
    verdict_lower = str(verdict).lower()

    if 'достоверно' in verdict_lower or 'true' in verdict_lower or 'верно' in verdict_lower:
        emoji = "✅"
        status = "ДОСТОВЕРНО"
    elif 'недостоверно' in verdict_lower or 'false' in verdict_lower or 'ложно' in verdict_lower:
        emoji = "❌"
        status = "НЕДОСТОВЕРНО"
    elif 'частично' in verdict_lower or 'partially' in verdict_lower:
        emoji = "⚠️"
        status = "ЧАСТИЧНО ДОСТОВЕРНО"
    else:
        emoji = "❓"
        status = verdict.upper()

    # Ограничиваем длину запроса для сообщения
    query_display = html.escape(query)
    if len(query_display) > 300:
        query_display = query_display[:300] + "..."

    message = f"{emoji} <b>Вердикт: {status}</b>\n\n"
    message += f"<i>Проверяемое утверждение:</i>\n{query_display}\n\n"
    message += "Для получения подробной информации с объяснением и источниками нажмите кнопку ниже."

    return message


def format_detailed_message(request_text, verdict, explanation, sources):
    """Форматирует подробное сообщение с объяснением и источниками"""
    # Ограничиваем длину запроса
    request_display = html.escape(request_text)
    if len(request_display) > 200:
        request_display = request_display[:200] + "..."

    message = f"<b>📋 Подробный анализ</b>\n\n"
    message += f"<b>Проверяемое утверждение:</b>\n{request_display}\n\n"

    # Вердикт
    verdict_lower = str(verdict).lower()
    if 'достоверно' in verdict_lower:
        message += f"<b>✅ Вердикт:</b> ДОСТОВЕРНО\n\n"
    elif 'недостоверно' in verdict_lower:
        message += f"<b>❌ Вердикт:</b> НЕДОСТОВЕРНО\n\n"
    elif 'частично' in verdict_lower:
        message += f"<b>⚠️ Вердикт:</b> ЧАСТИЧНО ДОСТОВЕРНО\n\n"
    else:
        message += f"<b>🔍 Вердикт:</b> {html.escape(str(verdict)[:50])}\n\n"

    # Объяснение
    if explanation and explanation != 'Нет объяснения':
        # Ограничиваем длину объяснения
        explanation_text = html.escape(str(explanation))
        if len(explanation_text) > 800:
            explanation_text = explanation_text[:800] + "...\n\n<i>(сообщение сокращено из-за ограничений Telegram)</i>"
        message += f"<b>📝 Объяснение:</b>\n{explanation_text}\n\n"

    # Источники
    if sources and len(sources) > 0:
        message += f"<b>🔗 Источники:</b>\n"
        sources_count = 0
        for i, source in enumerate(sources[:3], 1):  # Ограничиваем 3 источниками
            if isinstance(source, dict):
                if 'url' in source:
                    url = source['url']
                    title = source.get('title', 'Ссылка')
                    # Ограничиваем длину заголовка
                    if len(title) > 50:
                        title = title[:50] + "..."
                    message += f"{i}. <a href='{url}'>{html.escape(title)}</a>\n"
                    sources_count += 1
                elif 'title' in source:
                    title = source['title']
                    if len(title) > 50:
                        title = title[:50] + "..."
                    message += f"{i}. {html.escape(title)}\n"
                    sources_count += 1
            elif isinstance(source, str):
                source_text = source
                if len(source_text) > 50:
                    source_text = source_text[:50] + "..."
                message += f"{i}. {html.escape(source_text)}\n"
                sources_count += 1

        if sources_count == 0:
            message += "<i>Источники не указаны</i>"
    else:
        message += "<i>Источники не указаны</i>"

    return message


def split_long_message(message, max_length=3000):
    """Разделяет длинное сообщение на части"""
    if len(message) <= max_length:
        return [message]

    parts = []
    while len(message) > max_length:
        # Находим последний перенос строки или точку перед max_length
        split_pos = message.rfind('\n', 0, max_length)
        if split_pos == -1:
            split_pos = message.rfind('. ', 0, max_length)
            if split_pos != -1:
                split_pos += 1
        if split_pos == -1:
            split_pos = max_length

        parts.append(message[:split_pos].strip())
        message = message[split_pos:].strip()

    if message:
        parts.append(message)

    return parts


# Обработчик команды /start
@bot.message_handler(commands=["start", "main"])
def send_welcome(message):
    """Обрабатывает команду /start и /main."""
    print_user_request(message.from_user, "/start command")
    welcome_text = """
Привет! Я бот для проверки фактов. 

Выберите действие:
"""
    bot.send_message(message.chat.id, welcome_text, reply_markup=create_nav_buttons())


# Обработчик inline-кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_inline_buttons(call):
    """Обрабатывает нажатия inline-кнопок"""
    try:
        if call.data == "fact_check":
            try:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=call.message.text,
                    reply_markup=None
                )
            except:
                pass
            msg = bot.send_message(call.message.chat.id, "Отправьте текст или факт для проверки:")
            bot.register_next_step_handler(msg, process_fact_check)

        elif call.data == "history":
            # Показываем историю для пользователя, который нажал кнопку
            user_id = call.from_user.id
            chat_id = call.message.chat.id

            # Проверяем наличие истории
            cursor.execute("SELECT COUNT(*) FROM user_requests WHERE user_id=?", (user_id,))
            count = cursor.fetchone()[0]

            if count == 0:
                bot.send_message(
                    chat_id,
                    "У вас пока нет истории запросов. Сначала проверьте несколько фактов!",
                    reply_markup=create_nav_buttons()
                )
            else:
                # Получаем историю
                history = get_user_history(user_id)

                # Формируем сообщение с историей
                response_parts = []
                current_part = "📜 Ваша история запросов:\n\n"

                for i, (req_id, request, response_text, timestamp) in enumerate(history, 1):
                    # Получаем вердикт для отображения
                    details = get_request_details(req_id)
                    if details and details[2]:  # detailed_response
                        try:
                            response_data = json.loads(details[2])
                            verdict = response_data.get('verdict', response_text[:20])
                        except:
                            verdict = response_text[:20]
                    else:
                        verdict = response_text[:20]

                    # Ограничиваем длину запроса
                    request_display = request[:30]
                    if len(request) > 30:
                        request_display += "..."

                    entry = f"🔹 Запрос #{i} ({timestamp})\n"
                    entry += f"❓ {request_display}\n"
                    entry += f"📌 Вердикт: {verdict}\n\n"

                    # Если текущая часть становится слишком длинной, сохраняем и начинаем новую
                    if len(current_part) + len(entry) > 3000:
                        response_parts.append(current_part)
                        current_part = "📜 Продолжение истории:\n\n"

                    current_part += entry

                if current_part:
                    response_parts.append(current_part)

                # Отправляем части истории
                for i, part in enumerate(response_parts):
                    if i == len(response_parts) - 1:
                        # Последняя часть с кнопками
                        bot.send_message(
                            chat_id,
                            part,
                            reply_markup=create_nav_buttons()
                        )
                    else:
                        # Промежуточные части без кнопок
                        bot.send_message(chat_id, part)

            # Убираем кнопки из предыдущего сообщения
            try:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=call.message.text,
                    reply_markup=None
                )
            except:
                pass

        elif call.data.startswith("details_"):
            # Обработка кнопки "Подробнее"
            request_id = int(call.data.split("_")[1])
            details = get_request_details(request_id)

            if details:
                request_text, response_text, detailed_response, timestamp = details

                # Парсим сохраненный ответ
                if detailed_response:
                    try:
                        response_data = json.loads(detailed_response)
                        verdict = response_data.get('verdict', response_text)
                        explanation = response_data.get('explanation', 'Нет объяснения')
                        sources = response_data.get('sources', [])
                    except:
                        verdict = response_text
                        explanation = 'Нет детальной информации'
                        sources = []
                else:
                    verdict = response_text
                    explanation = 'Нет детальной информации'
                    sources = []

                # Форматируем подробное сообщение
                detailed_message = format_detailed_message(request_text, verdict, explanation, sources)

                # Проверяем длину сообщения
                if len(detailed_message) > 3000:
                    # Если все еще слишком длинное, делаем его еще короче
                    detailed_message = f"<b>📋 Подробный анализ</b>\n\n"
                    detailed_message += f"<b>Проверяемое утверждение:</b>\n{html.escape(request_text[:100])}...\n\n"
                    detailed_message += f"<b>Вердикт:</b> {html.escape(str(verdict)[:50])}\n\n"
                    detailed_message += f"<i>Полный анализ слишком длинный для отображения в Telegram.</i>\n"
                    detailed_message += f"<i>Вердикт: {html.escape(str(verdict)[:100])}</i>"

                # Отправляем сообщение
                bot.send_message(
                    call.message.chat.id,
                    detailed_message,
                    parse_mode='HTML',
                    disable_web_page_preview=True,
                    reply_markup=create_nav_buttons()
                )
            else:
                bot.send_message(
                    call.message.chat.id,
                    "Информация о запросе не найдена.",
                    reply_markup=create_nav_buttons()
                )

        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Ошибка обработки кнопки: {e}")
        # Пытаемся отправить сообщение об ошибке
        try:
            bot.send_message(
                call.message.chat.id,
                f"Произошла ошибка при обработке запроса. Попробуйте еще раз.",
                reply_markup=create_nav_buttons()
            )
        except:
            pass


def show_history(message):
    """Показывает историю запросов для конкретного пользователя"""
    user = message.from_user
    print_user_request(user, "show history")

    history = get_user_history(user.id)

    if not history:
        bot.send_message(
            message.chat.id,
            "У вас пока нет истории запросов. Сначала проверьте несколько фактов!",
            reply_markup=create_nav_buttons()
        )
        return

    response_parts = []
    current_part = "📜 Ваша история запросов:\n\n"

    for i, (req_id, request, response_text, timestamp) in enumerate(history, 1):
        # Получаем вердикт для отображения
        details = get_request_details(req_id)
        if details and details[2]:  # detailed_response
            try:
                response_data = json.loads(details[2])
                verdict = response_data.get('verdict', response_text[:20])
            except:
                verdict = response_text[:20]
        else:
            verdict = response_text[:20]

        # Ограничиваем длину запроса
        request_display = request[:30]
        if len(request) > 30:
            request_display += "..."

        entry = f"🔹 Запрос #{i} ({timestamp})\n"
        entry += f"❓ {request_display}\n"
        entry += f"📌 Вердикт: {verdict}\n\n"

        # Если текущая часть становится слишком длинной, сохраняем и начинаем новую
        if len(current_part) + len(entry) > 3000:
            response_parts.append(current_part)
            current_part = "📜 Продолжение истории:\n\n"

        current_part += entry

    if current_part:
        response_parts.append(current_part)

    # Отправляем части истории
    for i, part in enumerate(response_parts):
        if i == len(response_parts) - 1:
            # Последняя часть с кнопками
            bot.send_message(
                message.chat.id,
                part,
                reply_markup=create_nav_buttons()
            )
        else:
            # Промежуточные части без кнопок
            bot.send_message(message.chat.id, part)


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

        # Проверяем длину запроса
        if len(user_query) > 800:
            bot.send_message(
                message.chat.id,
                "Запрос слишком длинный. Пожалуйста, ограничьте его 800 символами.",
                reply_markup=create_nav_buttons()
            )
            return

        # Показываем статус "печатает"
        bot.send_chat_action(message.chat.id, 'typing')

        # Отправляем сообщение о обработке
        processing_msg = bot.send_message(message.chat.id, "◌ Подождите, идёт обработка запроса...")

        # Получаем структурированный ответ от API
        fact_check_result = get_fact_check(user_query)

        # Сохраняем в базу данных
        request_id = save_user_request(
            user,
            user_query,
            fact_check_result['verdict'],
            json.dumps(fact_check_result, ensure_ascii=False)
        )

        # Форматируем сообщение с вердиктом
        verdict_message = format_verdict_message(fact_check_result['verdict'], user_query)

        # Создаем кнопку "Подробнее" с ID запроса
        detail_markup = create_detail_button(request_id)

        # Удаляем сообщение об обработке
        bot.delete_message(message.chat.id, processing_msg.message_id)

        # Отправляем вердикт с кнопкой "Подробнее"
        bot.send_message(
            message.chat.id,
            verdict_message,
            parse_mode='HTML',
            reply_markup=detail_markup
        )

    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"Произошла ошибка: {str(e)}",
            reply_markup=create_nav_buttons()
        )


if __name__ == "__main__":
    print("Бот запущен и готов к работе!")

    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка в работе бота: {e}")
    finally:
        conn.close()