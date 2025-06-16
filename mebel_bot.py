import os
import telebot
import pandas as pd
from flask import Flask, request

# === Настройки ===
TOKEN = '7543140470:AAHAn7LEJPXrN457kK3CcfohP6Us9YE9Aao'
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://mebel-bot.onrender.com{WEBHOOK_PATH}"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# === Загрузка Excel ===
excel = pd.ExcelFile("Мебель (1).xlsx")
sheets = {str(name).strip(): excel.parse(name) for name in excel.sheet_names}
AVAILABLE_ROOMS = list(sheets.keys())

ICON_MAP = {
    "кровать": "🛏️", "матрас": "🧳", "окно": "🪟", "балкон": "🚪", "дверь": "🚪",
    "гарнитур": "🍽️", "шкафчик": "🗄️", "стол": "🪑", "стул": "💺", "ванна": "🛁",
    "раковина": "🚰", "изголовье": "🖼️", "диван": "🛋️", "тумба": "🛌",
    "сейф": "🔐", "шкаф": "🗄️", "зеркало": "🖼️", "подоконник": "🪞"
}

user_data = {}

def get_room_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [telebot.types.KeyboardButton(room) for room in AVAILABLE_ROOMS]
    for i in range(0, len(buttons), 3):
        markup.row(*buttons[i:i+3])
    return markup

def get_furniture_types_with_icons(room_key):
    sheet = sheets[room_key]
    if "Мебель" not in sheet.columns:
        return []
    result = []
    for ft in sheet["Мебель"].dropna().unique():
        icon = next((emoji for key, emoji in ICON_MAP.items() if key in ft.lower()), "🪑")
        result.append((f"{icon} {ft.strip()}", ft.strip()))
    return result

def get_furniture_keyboard(room_key):
    items = get_furniture_types_with_icons(room_key)
    if not items:
        return None
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [telebot.types.KeyboardButton(icon) for icon, orig in items]
    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])
    markup.add(telebot.types.KeyboardButton("🔙 Назад"))
    return markup

WELCOME_MESSAGE = (
    "🔑 Добро пожаловать!\n"
    "Я — виртуальный помощник отеля *«Золотой ключик»*.\n"
    "Напишите, например, `кровать 10` или выберите номер:"
)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.send_message(message.chat.id, WELCOME_MESSAGE, parse_mode="Markdown")
    bot.send_message(message.chat.id, "🔢 Выберите номер комнаты:", reply_markup=get_room_keyboard())

@bot.message_handler(func=lambda m: m.text.strip() in AVAILABLE_ROOMS)
def choose_room(message):
    room_key = message.text.strip()
    user_data[message.chat.id] = {"room": room_key}
    bot.send_message(
        message.chat.id,
        f"🛋 Комната *{room_key}* выбрана. Выберите мебель:",
        parse_mode="Markdown",
        reply_markup=get_furniture_keyboard(room_key)
    )

@bot.message_handler(func=lambda m: m.text == "🔙 Назад")
def go_back(message):
    send_welcome(message)

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    text = message.text.lower().strip()
    chat_id = message.chat.id

    parts = text.split()
    if len(parts) == 2:
        item_part, room_key = parts
        room_key = room_key.strip()

        if room_key in sheets:
            df = sheets[room_key]
            found = df[df['Мебель'].astype(str).str.contains(item_part, case=False, na=False)]
            if found.empty:
                bot.send_message(chat_id, f"🔍 В комнате *{room_key}* не найдено: *{item_part}*", parse_mode="Markdown")
                return

            reply = f"📦 Найдено в комнате *{room_key}*:\n\n"
            for _, row in found.iterrows():
                name = str(row.get('Мебель', '–')).strip()
                count = str(row.get('Кол-во', '–')).strip()
                length = str(row.get('Длина', '–')).strip()
                width = str(row.get('Ширина', '–')).strip()
                height = str(row.get('Высота', '–')).strip()

                size = width if "×" in width else f"{length}×{width}×{height}"
                size = size.replace(".0", "")
                icon = next((emoji for key, emoji in ICON_MAP.items() if key in name.lower()), "🪑")
                reply += f"{icon} {name} — {count} шт., размер: {size}\n"

            bot.send_message(chat_id, reply, parse_mode="Markdown")
            return

    room_key = user_data.get(chat_id, {}).get("room")
    if room_key:
        items = get_furniture_types_with_icons(room_key)
        selected = next((orig for icon, orig in items if icon == message.text or orig == message.text), None)
        if selected:
            df = sheets[room_key]
            found = df[df['Мебель'] == selected]
            reply = f"📦 В комнате *{room_key}* найдено:\n\n"
            for _, row in found.iterrows():
                name = str(row.get('Мебель', '–')).strip()
                count = str(row.get('Кол-во', '–')).strip()
                length = str(row.get('Длина', '–')).strip()
                width = str(row.get('Ширина', '–')).strip()
                height = str(row.get('Высота', '–')).strip()

                size = width if "×" in width else f"{length}×{width}×{height}"
                size = size.replace(".0", "")
                icon = next((emoji for key, emoji in ICON_MAP.items() if key in name.lower()), "🪑")
                reply += f"{icon} {name} — {count} шт., размер: {size}\n"
            bot.send_message(chat_id, reply, parse_mode="Markdown")
            return

    bot.send_message(chat_id, "❓ Не понял запрос. Введите, например: `кровать 10`", parse_mode="Markdown")

# === Flask routes ===
@app.route("/", methods=["GET"])
def index():
    return "Бот работает!"

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "OK", 200

# === Запуск ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=port)
