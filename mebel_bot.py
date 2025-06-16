import os
import pandas as pd
import telebot
from flask import Flask, request
from telebot import types

# === 1. Загрузка Excel ===
excel = pd.ExcelFile("Мебель (1).xlsx")
sheets = {str(name).strip(): excel.parse(name) for name in excel.sheet_names}
AVAILABLE_ROOMS = list(sheets.keys())

# === 2. Бот и Flask ===
TOKEN = '7543140470:AAHAn7LEJPXrN457kK3CcfohP6Us9YE9Aao'
bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)
user_data = {}

# === 3. Иконки ===
ICON_MAP = {
    "кровать": "🛏️", "матрас": "🧳", "окно": "🪟", "балкон": "🚪", "дверь": "🚪",
    "гарнитур": "🍽️", "шкафчик": "🗄️", "стол": "📏", "стул": "💺", "ванна": "🛁",
    "раковина": "🚰", "изголовье": "🖼️", "диван": "🛋️", "тумба": "🛌", "сейф": "🔐",
    "шкаф": "🗄️", "зеркало": "🖼️", "подоконник": "🪞"
}

# === 4. Приветствие ===
WELCOME_MESSAGE = (
    "🔑 *Добро пожаловать!*\n"
    "Я — виртуальный помощник отеля *«Золотой ключик»*.\n\n"
    "Моя задача — помогать тебе с поиском информации о мебели в наших номерах.\n"
    "Хочешь узнать, есть ли *кровать* в номере *10* или *телевизор* в номере *2*? Просто напиши:\n\n"
    "🗣 `кровать 10`\n"
    "🗣 `телевизор 2`\n\n"
    "📋 Я быстро найду нужную информацию: количество, размеры и даже особенности, если они есть.\n\n"
    "Если что-то непонятно — нажми на кнопку ниже или задай вопрос 🛎️"
)

# === 5. Клавиатуры ===
def get_room_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [types.KeyboardButton(room) for room in AVAILABLE_ROOMS]
    for i in range(0, len(buttons), 3):
        markup.row(*buttons[i:i+3])
    return markup

def get_furniture_types_with_icons(room_key):
    sheet = sheets[room_key]
    if "Мебель" not in sheet.columns:
        return []
    items = sheet["Мебель"].dropna().unique()
    result = []
    for item in items:
        icon = next((emoji for word, emoji in ICON_MAP.items() if word in item.lower()), "🪑")
        result.append((f"{icon} {item.strip()}", item.strip()))
    return result

def get_furniture_keyboard(room_key):
    items = get_furniture_types_with_icons(room_key)
    if not items:
        return None
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [types.KeyboardButton(icon) for icon, _ in items]
    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])
    markup.add(types.KeyboardButton("🔙 Назад"))
    return markup

# === 6. Старт ===
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔢 Выбрать номер комнаты", callback_data="choose_room"))
    bot.send_message(message.chat.id, WELCOME_MESSAGE, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "choose_room")
def handle_choose_room(call):
    bot.send_message(call.message.chat.id, "🔢 Выберите номер комнаты:", reply_markup=get_room_keyboard())

# === 7. Выбор комнаты ===
@bot.message_handler(func=lambda m: m.text in AVAILABLE_ROOMS)
def choose_furniture(message):
    user_data[message.chat.id] = {"room": message.text}
    bot.send_message(message.chat.id, f"Вы выбрали комнату {message.text}. Теперь выберите мебель:",
                     reply_markup=get_furniture_keyboard(message.text))

# === 8. Выбор мебели ===
@bot.message_handler(func=lambda m: any(m.text in (ft[0], ft[1]) for r in sheets for ft in get_furniture_types_with_icons(r)))
def show_info(message):
    chat_id = message.chat.id
    room_key = user_data.get(chat_id, {}).get("room")
    if not room_key:
        bot.send_message(chat_id, "⚠ Пожалуйста, выберите номер комнаты сначала.")
        return
    selected = message.text.strip()
    furniture = get_furniture_types_with_icons(room_key)
    item_name = next((orig for icon, orig in furniture if selected in (icon, orig)), None)
    sheet = sheets[room_key]
    found = sheet[sheet['Мебель'] == item_name]
    if found.empty:
        bot.send_message(chat_id, f"🔍 В комнате {room_key} не найдено: {item_name}")
        return
    reply = f"📦 Найдено в комнате *{room_key}*:\n\n"
    for _, row in found.iterrows():
        name = row.get("Мебель", "—")
        count = str(row.get("Кол-во", "–"))
        l, w, h = [str(row.get(x, "–")) for x in ["Длина", "Ширина", "Высота"]]
        size = f"{l}×{w}×{h}" if "×" not in w else w
        size = size.replace(".0×", "×").replace(".0", "")
        icon = next((emoji for key, emoji in ICON_MAP.items() if key in str(name).lower()), "🪑")
        reply += f"{icon} {name}\n🔢 Кол-во: {count}\n📐 Размеры: {size}\n──────────────\n"
    bot.send_message(chat_id, reply, parse_mode="Markdown")

# === 9. Назад ===
@bot.message_handler(func=lambda m: m.text == "🔙 Назад")
def go_back(message):
    send_welcome(message)

# === 10. Поиск текстом ===
@bot.message_handler(func=lambda m: True)
def search_text(message):
    parts = message.text.lower().split()
    if len(parts) != 2:
        return
    item, room = parts
    if room not in sheets:
        bot.send_message(message.chat.id, f"🚫 Комната {room} не найдена.")
        return
    sheet = sheets[room]
    found = sheet[sheet['Мебель'].astype(str).str.contains(item, case=False, na=False)]
    if found.empty:
        bot.send_message(message.chat.id, f"🔍 В комнате {room} не найдено: {item}")
        return
    reply = f"📦 Найдено в комнате *{room}*:\n\n"
    for _, row in found.iterrows():
        name = str(row['Мебель'])
        count = str(row.get('Кол-во', "–"))
        l, w, h = [str(row.get(x, "–")) for x in ["Длина", "Ширина", "Высота"]]
        size = f"{l}×{w}×{h}" if "×" not in w else w
        size = size.replace(".0×", "×").replace(".0", "")
        icon = next((emoji for key, emoji in ICON_MAP.items() if key in name.lower()), "🪑")
        reply += f"{icon} {name}\n🔢 Кол-во: {count}\n📐 Размеры: {size}\n──────────────\n"
    bot.send_message(message.chat.id, reply, parse_mode="Markdown")

# === 11. Flask webhook ===
@server.route("/" + TOKEN, methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "", 200

@server.route("/", methods=['GET'])
def index():
    return "Бот работает"

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"https://mebel-bot.onrender.com/{TOKEN}")
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
