import telebot
from groq import Groq
import os, base64
from flask import Flask, request

# 1. Настройки
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
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '!', 200
    else:
        return 'Bad Request', 403

@app.route('/')
def health():
    return "OK", 200

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет бро, как поживаешь?")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        print("--- Бот получил фото ---")
        # 1. Получаем фото в максимальном качестве
        file_info = bot.get_file(message.photo[-1].file_id)
        img_bytes = bot.download_file(file_info.file_path)
        base64_img = base64.b64encode(img_bytes).decode('utf-8')
        
        user_text = message.caption if message.caption else "Что скажешь по этому поводу, бро?"

        # 2. Запрос к Groq с Vision моделью
        # Важно: модель Llama 3.2 11B Vision требует строгого формата
        completion = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{MY_BRIEF}\n\nПользователь спрашивает: {user_text}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_img}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.7,
            max_tokens=1024
        )
        
        ans = completion.choices[0].message.content
        bot.reply_to(message, ans)
        print("--- Groq успешно ответил на фото ---")

    except Exception as e:
        # ТУТ САМОЕ ВАЖНОЕ: выводим ошибку в консоль Render
        print(f"❌ ОШИБКА В ФОТО: {str(e)}")
        bot.reply_to(message, "Брат, зрение подвело, чёт мутно там всё... Видимо, Groq капризничает.")

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.chat.id
    if uid not in chats_history:
        chats_history[uid] = [{"role": "system", "content": MY_BRIEF}]
    
    chats_history[uid].append({"role": "user", "content": message.text})
    
    if len(chats_history[uid]) > 12:
        chats_history[uid] = [chats_history[uid][0]] + chats_history[uid][-10:]
    
    try:
        ans = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chats_history[uid],
            temperature=0.7
        ).choices[0].message.content
        
        chats_history[uid].append({"role": "assistant", "content": ans})
        bot.send_message(uid, ans)
    except Exception as e:
        print(f"❌ ОШИБКА В ТЕКСТЕ: {e}")
        bot.send_message(uid, "Подвис, бро. Мозги закипели.")

if __name__ == "__main__":
    # Сбрасываем вебхук перед установкой, чтобы не было ошибки 409
    bot.remove_webhook()
    if WEBHOOK_URL:
        bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
        print(f"Webhook set to: {WEBHOOK_URL}/{TOKEN}")
    
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
