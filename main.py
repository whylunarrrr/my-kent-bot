import telebot
from groq import Groq
import os, base64
from flask import Flask, request

TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_KEY = os.environ.get("GROQ_API_KEY")
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")

bot = telebot.TeleBot(TOKEN)
client = Groq(api_key=GROQ_KEY)

chats_history = {}
MY_BRIEF = "Ты — Кент, бро. Стиль: неформальный, на 'ты', с юмором. Твоя самая первая фраза всегда: 'Привет бро, как поживаешь?'. Ты видишь фото и болтаешь."

app = Flask(__name__)

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.method == 'POST' and request.headers.get('content-type') == 'application/json':
        print("--- ВЕБХУК: ПОЛУЧЕН ЗАПРОС ---")
        try:
            json_data = request.get_json() 
            if json_data is None:
                print("--- ВЕБХУК: JSON ПУСТОЙ ---")
                return 'OK', 200 
            update = telebot.types.Update.de_json(json_data) 
            if update.message:
                print(f"--- ВЕБХУК: ТИП {update.message.content_type} ---")
            bot.process_new_updates([update])
            return 'OK', 200
        except Exception as e:
            print(f"--- ВЕБХУК ОШИБКА: {str(e)} ---")
            return 'OK', 200 
    return 'OK', 200

@app.route('/')
def health():
    return "OK", 200 bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет бро, как поживаешь?")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    print("--- ФОТО: ОБРАБОТКА ---")
    uid = message.chat.id
    if uid not in chats_history:
        chats_history[uid] = [{"role": "system", "content": MY_BRIEF}]
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        img_bytes = bot.download_file(file_info.file_path)
        base64_img = base64.b64encode(img_bytes).decode('utf-8')
        user_text = message.caption if message.caption else "Что на фото, бро?"
        completion = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": f"{MY_BRIEF}\n{user_text}"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
            ]}],
            temperature=0.7, max_tokens=1024
        )
        ans = completion.choices[0].message.content
        bot.reply_to(message, ans)
    except Exception as e:
        print(f"--- ОШИБКА ФОТО: {str(e)} ---")
        bot.reply_to(message, "Бро, в глазах поплыло, не вижу фото.")

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.chat.id
    if uid not in chats_history:
        chats_history[uid] = [{"role": "system", "content": MY_BRIEF}]
    chats_history[uid].append({"role": "user", "content": message.text})
    if len(chats_history[uid]) > 10:
        chats_history[uid] = [chats_history[uid][0]] + chats_history[uid][-9:]
    try:
        ans = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chats_history[uid],
            temperature=0.7
        ).choices[0].message.content
        chats_history[uid].append({"role": "assistant", "content": ans})
        bot.send_message(uid, ans)
    except Exception as e:
        bot.send_message(uid, "Мозги закипели,бро")if __name__ == "__main__":
    bot.remove_webhook()
    if WEBHOOK_URL:
        bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
