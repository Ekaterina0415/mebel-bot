import telebot
import pandas as pd
from telebot import types

# === 1. Загрузка Excel файла ===
excel = pd.ExcelFile("Мебель (1).xlsx")
sheets = {str(name).strip(): excel.parse(name) for name in excel.sheet_names}

# === 2. Настройки бота ===
TOKEN = '7543140470:AAHAn7LEJPXrN457kK3CcfohP6Us9YE9Aao'  # Ваш токен
bot = telebot.TeleBot(TOKEN)

# === 3. Хранение состояния пользователя ===
user_data = {}

# === 4. Иконки для мебели ===
ICON_MAP = {
    "кровать": "🛏️",
    "матрас": "🧳",
    "окно": "🪟",
    "балкон": "🚪",
    "дверь": "🚪",
    "гарнитур": "🍽️",
    "шкафчик": "🗄️",
    "стол": "🪑",
    "стул": "💺",
    "ванна": "🛁",
    "раковина": "🚰",
    "изголовье": "🖼️",
    "диван": "🛋️",
    "тумба": "🛌",
    "сейф": "🔐",
    "шкаф": "🗄️",
    "зеркало": "🖼️",
    "подоконник": "🪞"
}

# === 5. Сообщение приветствия ===
WELCOME_MESSAGE = (
    "🔑 Добро пожаловать!\n"
    "Я — виртуальный помощник отеля *«Золотой ключик»*.\n\n"
    "Моя задача — помогать тебе с поиском информации о мебели в наших номерах.\n"
    "Хочешь узнать, есть ли кровать в номере 10 или телевизор в номере 2? Просто напиши:\n\n"
    "🗣 *кровать 10*\n"
    "🗣 *телевизор 2*\n\n"
    "📋 Я быстро найду нужную информацию: количество, размеры и даже особенности, если они есть.\n\n"
    "Если что-то непонятно — нажми на кнопку ниже или задай вопрос 🛎️"
)

# === 6. Получить список доступных комнат ===
AVAILABLE_ROOMS = list(sheets.keys())

# === 7. Функция: клавиатура с номерами комнат ===
def get_room_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [types.KeyboardButton(room) for room in AVAILABLE_ROOMS]
    for i in range(0, len(buttons), 3):
        markup.row(*buttons[i:i+3])
    return markup

# === 8. Получить уникальные типы мебели для комнаты с иконками ===
def get_furniture_types_with_icons(room_key):
    sheet = sheets[room_key]
    if "Мебель" not in sheet.columns:
        return []

    furniture_types = sheet["Мебель"].dropna().unique()
    result = []
    for ft in furniture_types:
        icon = "🪑"  # иконка по умолчанию
        for keyword, emoji in ICON_MAP.items():
            if keyword.lower() in ft.lower():
                icon = emoji
                break
        result.append((icon + " " + ft.strip(), ft.strip()))  # Например: "🪑 Стул", "Стул"

    return result

# === 9. Функция: клавиатура с типами мебели для конкретной комнаты ===
def get_furniture_keyboard(room_key):
    items = get_furniture_types_with_icons(room_key)
    if not items:
        return None

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [types.KeyboardButton(icon_name) for icon_name, orig_name in items]
    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])
    markup.add(types.KeyboardButton("🔙 Назад"))
    return markup

# === 10. Команда /start ===
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.send_message(message.chat.id, WELCOME_MESSAGE, parse_mode="Markdown")
    bot.send_message(message.chat.id, "🔢 Выберите номер комнаты:", reply_markup=get_room_keyboard())

# === 11. Обработка выбора номера комнаты ===
@bot.message_handler(func=lambda m: m.text.strip() in AVAILABLE_ROOMS)
def choose_furniture_type(message):
    room_key = message.text.strip()
    user_data[message.chat.id] = {"room": room_key}
    bot.send_message(
        message.chat.id,
        f"🛋 Выбрана комната *{room_key}*. Выберите тип мебели:",
        parse_mode="Markdown",
        reply_markup=get_furniture_keyboard(room_key)
    )

# === 12. Обработка выбора типа мебели ===
@bot.message_handler(func=lambda m: any(ft[0] == m.text.strip() or ft[1] == m.text.strip() for ft in sum([get_furniture_types_with_icons(r) for r in sheets], [])))
def show_furniture_info(message):
    chat_id = message.chat.id
    selected_item = message.text.strip()
    room_key = user_data.get(chat_id, {}).get("room")

    if not room_key or room_key not in sheets:
        bot.send_message(chat_id, "⚠ Не выбрана комната.")
        return

    # Определяем, какая мебель запрошена
    furniture_list = get_furniture_types_with_icons(room_key)
    furniture_name = next((orig_name for icon_name, orig_name in furniture_list if icon_name == selected_item or orig_name == selected_item), None)

    if not furniture_name:
        bot.send_message(chat_id, "⚠ Тип мебели не распознан.")
        return

    sheet = sheets[room_key]
    found = sheet[sheet["Мебель"] == furniture_name]

    if found.empty:
        bot.send_message(chat_id, f"🔍 В комнате *{room_key}* не найдено: *{furniture_name}*", parse_mode="Markdown")
        return

    reply = f"📦 Найдено в комнате *{room_key}*:\n\n"
    for _, row in found.iterrows():
        name = str(row.get("Мебель", "неизвестно")).strip()
        count = str(row.get("Кол-во", "–")).strip()
        length = str(row.get("Длина", "–")).strip()
        width = str(row.get("Ширина", "–")).strip()
        height = str(row.get("Высота", "–")).strip()

        # Если ширина содержит × — это готовый размер
        if "×" in width:
            size = width
        else:
            size = f"{length}×{width}×{height}"

        # Убираем .0 из чисел
        size = size.replace(".0×", "×").replace(".0", "")

        # Автоматически подставляем иконку
        icon = next((emoji for key, emoji in ICON_MAP.items() if key.lower() in name.lower()), "🪑")

        reply += (
            f"{icon} Наименование: {name}\n"
            f"🔢 Количество: {count} шт.\n"
            f"📐 Размеры: {size}\n"
            f"──────────────\n"
        )

    bot.send_message(chat_id, reply, parse_mode="Markdown")

# === 13. Кнопка "Назад" ===
@bot.message_handler(func=lambda m: m.text == "🔙 Назад")
def go_back(message):
    send_welcome(message)

# === 14. Обработка текстовых команд вида "кровать 10" ===
@bot.message_handler(func=lambda m: True)
def handle_query(message):
    text = message.text.lower().strip()
    parts = text.split()

    if len(parts) != 2:
        return

    item_part, room_number = parts
    room_key = str(room_number).strip()

    if room_key not in sheets:
        available_rooms = ', '.join(sheets.keys())
        bot.send_message(
            message.chat.id,
            f"🚫 Комната *{room_key}* не найдена.\nДоступные номера: {available_rooms}",
            parse_mode="Markdown"
        )
        return

    sheet = sheets[room_key]
    if "Мебель" not in sheet.columns:
        bot.send_message(message.chat.id, f"⚠️ В комнате *{room_key}* нет колонки 'Мебель'", parse_mode="Markdown")
        return

    found = sheet[sheet['Мебель'].astype(str).str.contains(item_part, case=False, na=False)]

    if found.empty:
        bot.send_message(message.chat.id, f"🔍 В комнате *{room_key}* не найдено: *{item_part}*", parse_mode="Markdown")
        return

    reply = f"📦 Найдено в комнате *{room_key}*:\n\n"
    for _, row in found.iterrows():
        name = str(row.get('Мебель', 'неизвестно')).strip()
        count = str(row.get('Кол-во', '–')).strip()
        length = str(row.get('Длина', '–')).strip()
        width = str(row.get('Ширина', '–')).strip()
        height = str(row.get('Высота', '–')).strip()

        def clean(val):
            return val if "." not in str(val) else str(val).rstrip("0").rstrip(".") if "." in str(val) else val

        length, width, height = map(clean, [length, width, height])

        # Если ширина содержит × — это уже готовый размер
        if "×" in width:
            size = width
        else:
            size = f"{length}×{width}×{height}"

        icon = next((emoji for key, emoji in ICON_MAP.items() if key.lower() in name.lower()), "🪑")
        reply += (
            f"{icon} Наименование: {name}\n"
            f"🔢 Количество: {count} шт.\n"
            f"📐 Размеры: {size}\n"
            f"──────────────\n"
        )

    bot.send_message(message.chat.id, reply, parse_mode="Markdown")

# === 15. Запуск бота ===
print("✅ Бот запущен!")
bot.polling(none_stop=True)