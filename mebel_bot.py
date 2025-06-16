import telebot
import pandas as pd

from telebot import types

# === 1. Загрузка Excel файла ===
excel = pd.ExcelFile("Мебель (1).xlsx")
sheets = {str(name).strip(): excel.parse(name) for name in excel.sheet_names}

# === 2. Настройки бота ===
TOKEN = '7543140470:AAHAn7LEJPXrN457kK3CcfohP6Us9YE9Aao'
bot = telebot.TeleBot(TOKEN)

# === 3. Хранение состояния пользователя ===
user_data = {}

# === 4. Иконки для мебели ===
ICON_MAP = {
    "кровать": "🛏️",
    "матрас": "🛌",
    "окно": "🪟",
    "балкон": "🚪",
    "дверь": "🚪",
    "гарнитур": "🍽️",
    "шкафчик": "🗄️",
    "стол": "🪑",  # Можно заменить на 🪟 или другой, но этот — стол/табурет
    "стул": "💺",
    "ванна": "🛁",
    "раковина": "🚰",
    "изголовье": "🖼️",
    "диван": "🛋️",
    "тумба": "🛌",
    "сейф": "🔐",
    "шкаф": "🗄️",
    "зеркало": "🪞",
    "подоконник": "🪟",
    "телевизор": "📺"
}

# === 5. Приветственное сообщение ===
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

AVAILABLE_ROOMS = list(sheets.keys())

# === 6. Клавиатура с комнатами ===
def get_room_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [types.KeyboardButton(room) for room in AVAILABLE_ROOMS]
    for i in range(0, len(buttons), 3):
        markup.row(*buttons[i:i+3])
    return markup

# === 7. Типы мебели с иконками ===
def get_furniture_types_with_icons(room_key):
    sheet = sheets[room_key]
    if "Мебель" not in sheet.columns:
        return []

    furniture_types = sheet["Мебель"].dropna().unique()
    result = []
    for ft in furniture_types:
        icon = "🪑"
        for keyword, emoji in ICON_MAP.items():
            if keyword.lower() in ft.lower():
                icon = emoji
                break
        result.append((icon + " " + ft.strip(), ft.strip()))
    return result

# === 8. Клавиатура с типами мебели ===
def get_furniture_keyboard(room_key):
    items = get_furniture_types_with_icons(room_key)
    if not items:
        return None
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [types.KeyboardButton(icon_name) for icon_name, _ in items]
    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])
    markup.add(types.KeyboardButton("🔙 Назад"))
    return markup

# === 9. /start и /help ===
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.send_message(message.chat.id, WELCOME_MESSAGE, parse_mode="Markdown")
    bot.send_message(message.chat.id, "🔢 Выберите номер комнаты:", reply_markup=get_room_keyboard())

# === 10. Выбор комнаты ===
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

# === 11. Выбор типа мебели ===
@bot.message_handler(func=lambda m: any(m.text.strip() in [ft[0], ft[1]] for r in sheets for ft in get_furniture_types_with_icons(r)))
def show_furniture_info(message):
    chat_id = message.chat.id
    selected_item = message.text.strip()
    room_key = user_data.get(chat_id, {}).get("room")
    if not room_key or room_key not in sheets:
        bot.send_message(chat_id, "⚠ Не выбрана комната.")
        return
    furniture_list = get_furniture_types_with_icons(room_key)
    furniture_name = next((orig for icon, orig in furniture_list if icon == selected_item or orig == selected_item), None)
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
        size = width if "×" in width else f"{length}×{width}×{height}"
        size = size.replace(".0×", "×").replace(".0", "")
        icon = next((emoji for key, emoji in ICON_MAP.items() if key.lower() in name.lower()), "🪑")
        reply += (
            f"{icon} Наименование: {name}\n"
            f"🔢 Количество: {count} шт.\n"
            f"📐 Размеры: {size}\n"
            f"──────────────\n"
        )
    bot.send_message(chat_id, reply, parse_mode="Markdown")

# === 12. Назад ===
@bot.message_handler(func=lambda m: m.text == "🔙 Назад")
def go_back(message):
    send_welcome(message)

# === 13. Поиск по типу мебели и номеру ===
@bot.message_handler(func=lambda m: True)
def handle_query(message):
    text = message.text.lower().strip()
    parts = text.split()
    if len(parts) != 2:
        return
    item_part, room_number = parts
    room_key = str(room_number).strip()
    if room_key not in sheets:
        bot.send_message(message.chat.id, f"🚫 Комната *{room_key}* не найдена.", parse_mode="Markdown")
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
        size = width if "×" in width else f"{length}×{width}×{height}"
        size = size.replace(".0×", "×").replace(".0", "")
        icon = next((emoji for key, emoji in ICON_MAP.items() if key.lower() in name.lower()), "🪑")
        reply += (
            f"{icon} Наименование: {name}\n"
            f"🔢 Количество: {count} шт.\n"
            f"📐 Размеры: {size}\n"
            f"──────────────\n"
        )
    bot.send_message(message.chat.id, reply, parse_mode="Markdown")

# === 14. Запуск ===
print("✅ Бот запущен!")
bot.polling(none_stop=True)
