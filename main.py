import telebot
from groq import Groq
import os
import threading
import base64
from flask import Flask

# Настройки Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

MY_BRIEF = "Ты — Кент, реальный бро. Стиль: неформальный, на 'ты', с юмором. Если скинули фото — опиши, что видишь."

client = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)
chats_history = {}

app = Flask(__name__)
@app.route('/')
def health(): return "Кент видит всё!", 200

def encode_image(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        base64_img = encode_image(downloaded_file)
        
        response = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=
            }]
        )
        bot.reply_to(message, response.choices[0].message.content)
    except Exception as e:
        print(f"Error photo: {e}")
        bot.reply_to(message, "Брат, чет со зрением плохо...")

@bot.message_handler(func=lambda m: True)
def chat_handler(message):
    user_id = message.chat.id
    if user_id not in chats_history:
        chats_history[user_id] = [{"role": "system", "content": MY_BRIEF}]
    
    chats_history[user_id].append({"role": "user", "content": message.text})
    
    if len(chats_history[user_id]) > 10:
        # Упрощенная обрезка истории без лишних скобок
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
        print(f"Error text: {e}")
        bot.send_message(user_id, "Брат, чет я подвис.")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    print("Кент на связи!")
    bot.infinity_polling()
