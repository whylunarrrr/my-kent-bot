import telebot
from groq import Groq
import os
import threading
import time
import base64
from flask import Flask

# Берем данные из настроек Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

MY_BRIEF = "Ты — Кент, реальный бро. Стиль: неформальный, на 'ты', с юмором. Если скинули фото — опиши, что видишь, или ответь по контексту."

client = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)
chats_history = {}

# Веб-сервер для UptimeRobot
app = Flask(__name__)
@app.route('/')
def health(): return "Кент видит всё!", 200

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# ОБРАБОТКА ФОТО
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    temp_path = f"temp_{message.chat.id}_{message.message_id}.jpg"
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with open(temp_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        base_4_image = encode_image(temp_path)
        
        # Используем Vision модель для картинок
        response = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=
                }
            ]
        )
        
        answer = response.choices[0].message.content
        if answer:
            bot.reply_to(message, answer)
        else:
            bot.reply_to(message, "Брат, вижу, но слов нет...")
            
    except Exception as e:
        print(f"Ошибка фото: {e}")
        bot.reply_to(message, "Брат, чет со зрением плохо, не разберу...")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# ОБРАБОТКА ТЕКСТА
@bot.message_handler(func=lambda m: True)
def chat_handler(message):
    user_id = message.chat.id
    if user_id not in chats_history:
        chats_history[user_id] = [{"role": "system", "content": MY_BRIEF}]
    
    chats_history[user_id].append({"role": "user", "content": message.text})
    
    # Исправленная обрезка истории (системный промпт + 8 последних)
    if len(chats_history[user_id]) > 10:
        chats_history[user_id] = [chats_history[user_id][0]] + chats_history[user_id][-8:]
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chats_history[user_id]
        )
        answer = completion.choices[0].message.content
        if answer:
            chats_history[user_id].append({"role": "assistant", "content": answer})
            bot.send_message(user_id, answer)
    except Exception as e:
        print(f"Ошибка текста: {e}")
        bot.send_message(user_id, "Брат, чет я подвис. Дай мне секунду.")

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    print("Кент на связи и всё видит!")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
