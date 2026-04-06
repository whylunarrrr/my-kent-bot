import telebot
from openai import OpenAI
import os
import base64
import sys
import logging
from flask import Flask, request

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Берем переменные из окружения Render
TOKEN = os.environ.get('TELEGRAM_TOKEN')
OPENROUTER_KEY = os.environ.get('OPENROUTER_API_KEY')
WEBHOOK_URL = os.environ.get('RENDER_EXTERNAL_URL') # Убедись, что в Render эта переменная есть

bot = telebot.TeleBot(TOKEN)
client = OpenAI(base_url="https://openrouter.ai", api_key=OPENROUTER_KEY)

chats_history = {}
MY_BRIEF = "Ты — Кент, свой бро. Шаришь в тачках, технике, сленге. Отвечай кратко и по делу."

app = Flask(__name__)

def send_safe_message(chat_id, text):
    if not text: return
    if len(text) > 4000:
        for x in range(0, len(text), 4000):
            bot.send_message(chat_id, text[x:x+4000])
    else:
        bot.send_message(chat_id, text)

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return '', 403

@app.route('/')
def health():
    return "I am alive", 200

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    uid = message.chat.id
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        img_bytes = bot.download_file(file_info.file_path)
        base64_img = base64.b64encode(img_bytes).decode('utf-8')
        
        user_text = message.caption if message.caption else "Что тут на фото?"
        
        completion = client.chat.create( # У OpenRouter иногда метод сокращен
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
        send_safe_message(uid, ans)
    except Exception as e:
        logging.error(f"PHOTO ERROR: {e}")
        bot.reply_to(message, "Бро, чет не вижу нифига...")

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.chat.id
    if uid not in chats_history:
        chats_history[uid] = [{"role": "system", "content": MY_BRIEF}]
    
    chats_history[uid].append({"role": "user", "content": message.text})
    if len(chats_history[uid]) > 10:
        chats_history[uid] = [chats_history[uid][0]] + chats_history[uid][-9:]

    try:
        completion = client.chat.completions.create(
            model="google/gemini-2.0-flash-exp:free",
            messages=chats_history[uid]
        )
        ans = completion.choices[0].message.content
        chats_history[uid].append({"role": "assistant", "content": ans})
        send_safe_message(uid, ans)
    except Exception as e:
        logging.error(f"TEXT ERROR: {e}")
        bot.send_message(uid, "Мозги кипят...")

if __name__ == "__main__":
    # Важно для Render: сначала удаляем старый хук, потом ставим новый
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    # Render сам подставит PORT
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
