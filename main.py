import telebot
from openai import OpenAI
import os
import base64
import sys
import logging
from flask import Flask, request

# Принудительно выводим все логи в консоль Render
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Данные из переменных окружения Render
TOKEN = os.environ.get('TELEGRAM_TOKEN')
OPENROUTER_KEY = os.environ.get('OPENROUTER_API_KEY')
WEBHOOK_URL = os.environ.get('RENDER_EXTERNAL_URL')

bot = telebot.TeleBot(TOKEN)

# Настройка клиента OpenRouter
client = OpenAI(
  base_url="https://openrouter.ai",
  api_key=OPENROUTER_KEY,
)

chats_history = {}
MY_BRIEF = "Ты — Кент, бро. Стиль: информальный, на 'ты', с юмором. Твой создатель - whyhunarm."

app = Flask(__name__)

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    if request.method == 'POST' and request.headers.get('content-type') == 'application/json':
        json_data = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Error', 403

@app.route('/')
def health():
    return "OK", 200

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет бро, как поживаешь?")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    uid = message.chat.id
    if uid not in chats_history:
        chats_history[uid] = [{"role": "system", "content": MY_BRIEF}]
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        img_bytes = bot.download_file(file_info.file_path)
        base64_img = base64.b64encode(img_bytes).decode('utf-8')
        
        user_text = message.caption if message.caption else "Что на фото?"
        
        # Попробуем Gemini 2.0 Flash (бесплатная и мощная)
        completion = client.chat.completions.create(
            model="google/gemini-2.0-flash-exp:free",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                    ]
                }
            ]
        )
        ans = completion.choices.message.content
        bot.reply_to(message, ans)
    except Exception as e:
        print(f"!!! IMAGE ERROR: {e}", flush=True) # Ошибка появится в логах Render
        bot.reply_to(message, "Бро, с глазами беда, не вижу фото...")

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.chat.id
    if uid not in chats_history:
        chats_history[uid] = [{"role": "system", "content": MY_BRIEF}]
    
    chats_history[uid].append({"role": "user", "content": message.text})
    
    # Ограничиваем историю до 10 сообщений
    if len(chats_history[uid]) > 10:
        # Сохраняем системный промпт и последние 9 сообщений
        chats_history[uid] = [chats_history[uid][0]] + chats_history[uid][-9:]

    try:
        # Используем ту же модель для текста
        completion = client.chat.completions.create(
            model="google/gemini-2.0-flash-exp:free",
            messages=chats_history[uid]
        )
        ans = completion.choices.message.content
        chats_history[uid].append({"role": "assistant", "content": ans})
        bot.send_message(uid, ans)
    except Exception as e:
        print(f"!!! TEXT ERROR: {e}", flush=True) # Ошибка появится в логах Render
        bot.send_message(uid, "Мозги закипели, бро... Глянь логи.")

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
