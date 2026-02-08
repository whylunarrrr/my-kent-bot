import telebot
from groq import Groq
import os, threading, base64
from flask import Flask, request

# 1. Настройки
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_KEY = os.environ.get("GROQ_API_KEY")
# Render предоставляет этот URL автоматически
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")

bot = telebot.TeleBot(TOKEN)
client = Groq(api_key=GROQ_KEY)
chats_history = {}
MY_BRIEF = "Ты — Кент, бро. Стиль: неформальный, на 'ты', с юмором. Ты видишь фото и болтаешь."

app = Flask(__name__)

# Маршрут для обработки вебхуков от Telegram
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '!', 200
    else:
        return 'Bad Request', 403

# Маршрут для проверки работоспособности (Health Check)
@app.route('/')
def health():
    return "OK", 200

# 3. Исправленная обработка ФОТО (осталась прежней)
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        img_bytes = bot.download_file(file_info.file_path)
        base64_img = base64.b64encode(img_bytes).decode('utf-8')
        
        user_text = message.caption if message.caption else "Что скажешь по этому поводу, бро?"

        res = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=
                }
            ]
        )
        bot.reply_to(message, res.choices[0].message.content)
    except Exception as e:
        print(f"Error photo: {e}")
        bot.reply_to(message, "Брат, зрение подвело, чёт мутно там всё...")

# 4. Обработка ТЕКСТА (осталась прежней)
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.chat.id
    if uid not in chats_history:
        chats_history[uid] = [{"role": "system", "content": MY_BRIEF}]
    
    chats_history[uid].append({"role": "user", "content": message.text})
    
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
        bot.send_message(uid, "Подвис, бро. Мозги закипели.")

if __name__ == "__main__":
    # Устанавливаем вебхук при старте приложения
    if WEBHOOK_URL:
        bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    
    # Запуск Flask-приложения (оно слушает порт)
    port = int(os.environ.get("PORT", 8080))
    # use_reloader=False - важно для предотвращения двойного запуска
    app.run(host='0.0.0.0', port=port, use_reloader=False)
