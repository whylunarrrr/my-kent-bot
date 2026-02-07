import telebot
from groq import Groq
import os, threading, base64
from flask import Flask

# 1. Настройки (из Render)
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_KEY = os.environ.get("GROQ_API_KEY")
bot = telebot.TeleBot(TOKEN)
client = Groq(api_key=GROQ_KEY)
chats_history = {}
MY_BRIEF = "Ты — Кент, бро. Стиль: неформальный, на 'ты', с юмором. Ты видишь фото и болтаешь."

# 2. Веб-сервер
app = Flask(__name__)
@app.route('/')
def health(): return "OK", 200

# 3. Обработка ФОТО (Vision)
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        img_bytes = bot.download_file(file_info.file_path)
        base64_img = base64.encodebytes(img_bytes).decode('utf-8')
        
        # УПРОЩЕННЫЙ ЗАПРОС (БЕЗ ПЕРЕМЕННЫХ)
        res = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=
            }]
        )
        bot.reply_to(message, res.choices[0].message.content)
    except Exception as e:
        print(f"Error photo: {e}")
        bot.reply_to(message, "Брат, зрение подвело...")

# 4. Обработка ТЕКСТА
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.chat.id
    if uid not in chats_history:
        chats_history[uid] = [{"role": "system", "content": MY_BRIEF}]
    
    chats_history[uid].append({"role": "user", "content": message.text})
    
    # Супер-простая обрезка истории
    if len(chats_history[uid]) > 10:
        chats_history[uid] = [chats_history[uid][0]] + chats_history[uid][-8:]
    
    try:
        ans = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chats_history[uid]
        ).choices[0].message.content
        
        chats_history[uid].append({"role": "assistant", "content": ans})
        bot.send_message(uid, ans)
    except Exception as e:
        print(f"Error text: {e}")
        bot.send_message(uid, "Подвис, бро.")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()

