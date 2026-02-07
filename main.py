import telebot
from groq import Groq
import os
import threading
import base64
from flask import Flask

# 1. ЗАГРУЗКА НАСТРОЕК
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_KEY = os.environ.get("GROQ_API_KEY")

# 2. ИНИЦИАЛИЗАЦИЯ
bot = telebot.TeleBot(TOKEN)
client = Groq(api_key=GROQ_KEY)
chats_history = {}

MY_BRIEF = "Ты — Кент, реальный бро. Стиль: неформальный, на 'ты', с юмором. Ты умеешь видеть фото и болтать по душам."

# 3. ВЕБ-СЕРВЕР (ЧТОБЫ RENDER НЕ СПАЛ)
app = Flask(__name__)
@app.route('/')
def health(): return "Кент в здании!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 4. ФУНКЦИЯ ДЛЯ ОБРАБОТКИ КАРТИНКИ
def encode_image(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

# 5. ОБРАБОТКА ФОТО
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        # Получаем фото в лучшем качестве
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        base64_img = encode_image(downloaded_file)

        # Запрос к нейронке со зрение
        response = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=
            }]
        )
        bot.reply_to(message, response.choices[0].message.content)
    except Exception as e:
        print(f"Ошибка фото: {e}")
        bot.reply_to(message, "Брат, чет глаза замылились, не разберу...")

# 6. ОБРАБОТКА ТЕКСТА
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    user_id = message.chat.id
    if user_id not in chats_history:
        chats_history[user_id] = [{"role": "system", "content": MY_BRIEF}]

    # Добавляем сообщение юзера
    chats_history[user_id].append({"role": "user", "content": message.text})

    # Обрезка истории (храним системный промпт + последние 8 сообщений)
    if len(chats_history[user_id]) > 10:
        chats_history[user_id] = [chats_history[user_id][0]] + chats_history[user_id][-8:]

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chats_history[user_id]
        )
        answer = completion.choices[0].message.content
        chats_history[user_id].append({"role": "assistant", "content": answer})
        bot.send_message(user_id, answer)
    except Exception as e:
        print(f"Ошибка текста: {e}")
        bot.send_message(user_id, "Брат, чет я подвис. Повтори-ка!")

# 7. ЗАПУСК
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    print(">>> Кент вышел на связь!")
    bot.infinity_polling()
