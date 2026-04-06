import telebot
from openai import OpenAI
import os
import base64
import sys
import logging
from flask import Flask, request

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

TOKEN = os.environ.get('TELEGRAM_TOKEN')
OPENROUTER_KEY = os.environ.get('OPENROUTER_API_KEY')
WEBHOOK_URL = os.environ.get('RENDER_EXTERNAL_URL')

# Проверка переменных окружения
if not all([TOKEN, OPENROUTER_KEY, WEBHOOK_URL]):
    logging.error("Missing environment variables!")
    sys.exit(1)

bot = telebot.TeleBot(TOKEN)
client = OpenAI(
    base_url="https://openrouter.ai",
    api_key=OPENROUTER_KEY,
)

MY_BRIEF = "Ты — Кент, свой бро. Шаришь в тачках (Лавр, Марк, Слива), технике и сленге. Отвечай кратко и по делу."

chats_history = {}
app = Flask(__name__)

# Установка вебхука с обработкой ошибок
try:
    bot.remove_webhook()
    webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
    bot.set_webhook(url=webhook_url)
    logging.info(f"Webhook set to {webhook_url}")
except Exception as e:
    logging.error(f"Webhook setup error: {e}")

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return 'OK', 200
    except Exception as e:
        logging.error(f"Webhook processing error: {e}")
        return 'ERROR', 500

@app.route('/')
def health():
    return "OK", 200

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    uid = message.chat.id
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        img_bytes = bot.download_file(file_info.file_path)
        base64_img = base64.b64encode(img_bytes).decode('utf-8')
        user_text = message.caption if message.caption else "Что тут, бро?"
        
        completion = client.chat.completions.create(
            model="google/gemini-2.0-flash-exp:free",
            messages=[
                {"role": "system", "content": MY_BRIEF},
                {"role": "user", "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                ]}
            ]
        )
        ans = completion.choices[0].message.content
        bot.send_message(uid, ans)
    except Exception as e:
        logging.error(f"IMAGE ERROR: {e}")
        bot.reply_to(message, "Бро, чет зрение подводит...")

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.chat.id
    
    # Инициализация истории чата
    if uid not in chats_history:
        chats_history[uid] = [{"role": "system", "content": MY_BRIEF}]
    
    # Добавляем сообщение пользователя
    chats_history[uid].append({"role": "user", "content": message.text})
    
    # Ограничиваем длину истории (системное сообщение + последние 9 сообщений)
    if len(chats_history[uid]) > 10:
        chats_history[uid] = [chats_history[uid][0]] + chats_history[uid][-9:]

    try:
        completion = client.chat.completions.create(
            model="google/gemini-2.0-flash-exp:free",
            messages=chats_history[uid]
        )
        ans = completion.choices[0].message.content
        
        # Добавляем ответ ассистента в историю
        chats_history[uid].append({"role": "assistant", "content": ans})
        bot.send_message(uid, ans)
        
    except Exception as e:
        logging.error(f"TEXT ERROR: {e}")
        bot.send_message(uid, "Мозги закипели...")

# Опционально: обработка других типов сообщений
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    bot.reply_to(message, "Бро, голосовые пока не шарю. Напиши текстом или картинку кинь.")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    bot.reply_to(message, "Бро, документы не принимаю. Кидай картинку или пиши.")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
