import telebot
from groq import Groq
import os, base64
from flask import Flask, request

# 1. Берем настройки из переменных окружения Render
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_KEY = os.environ.get("GROQ_API_KEY")
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")

bot = telebot.TeleBot(TOKEN)
client = Groq(api_key=GROQ_KEY)

# Память чата
chats_history = {}
# Личность твоего бота
MY_BRIEF = "Ты — Кент, бро. Стиль: неформальный, на 'ты', с юмором. Твоя самая первая фраза всегда: 'Привет бро, как поживаешь?'. Ты видишь фото и болтаешь."

app = Flask(__name__)

# Вебхук: прием сообщений от Телеграма
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '!', 200
    else:
        return 'Forbidden', 403

@app.route('/')
def health():
    return "Кент на связи!", 200

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет бро, как поживаешь?")

# Обработка ФОТО
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        # 1. Качаем фото
        file_info = bot.get_file(message.photo[-1].file_id)
        img_bytes = bot.download_file(file_info.file_path)
        base64_img = base64.b64encode(img_bytes).decode('utf-8')
        
        user_text = message.caption if message.caption else "Что на фото, бро?"

        # 2. Запрос в Groq (Vision модель)
        res = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[
                {"role": "system", "content": MY_BRIEF},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
                        }
                    ]
                }
            ],
            max_tokens=1024
        )
        
        bot.reply_to(message, res.choices[0].message.content)
    except Exception as e:
        print(f"Ошибка на фото: {e}")
        bot.reply_to(message, "Брат, чет в глазах поплыло, не вижу ни черта...")

# Обработка ТЕКСТА
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.chat.id
    
    # Инициализация истории, если новый юзер
    if uid not in chats_history:
        chats_history[uid] = [{"role": "system", "content": MY_BRIEF}]
    
    chats_history[uid].append({"role": "user", "content": message.text})
    
    # Ограничение памяти (последние 10 сообщений)
    if len(chats_history[uid]) > 10:
        chats_history[uid] = [chats_history[uid][0]] + chats_history[uid][-9:]
    
    try:
        # Запрос в Groq (Текстовая модель)
        ans = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chats_history[uid],
            temperature=0.7
        ).choices[0].message.content
        
        chats_history[uid].append({"role": "assistant", "content": ans})
        bot.send_message(uid, ans)
    except Exception as e:
        print(f"Ошибка на тексте: {e}")
        bot.send_message(uid, "Мозги кипят, бро. Повтори позже.")

# Запуск
if __name__ == "__main__":
    # Убираем старый вебхук и ставим новый
    bot.remove_webhook()
    if WEBHOOK_URL:
        bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
        print(f"✅ Вебхук установлен: {WEBHOOK_URL}/{TOKEN}")
    
    # Запускаем Flask сервер
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
