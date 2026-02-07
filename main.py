import telebot
from groq import Groq
import os
import threading
import time
from flask import Flask

# --- ТВОИ ДАННЫЕ (ЗАМЕНИ НА НОВЫЕ!) ---
TELEGRAM_TOKEN = "8330753343:AAFCkTRbiBxN5INIMwE7RISd6PhYIY9aR9A"
GROQ_API_KEY = "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"

MY_BRIEF = """
Ты — Кент, реальный бро и универсальный собеседник. 
Стиль: неформальный, на "ты", с юмором. 
ПРАВИЛА: Не навязывай темы новеллы или авто, отвечай по контексту. Будь умным и не ломай слова.
"""

# Инициализация
client = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)
chats_history = {}

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (ЧТОБЫ НЕ СПАЛ) ---
app = Flask(name)
@app.route('/')
def health_check(): return "Кент в деле!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- ЛОГИКА БОТА ---
@bot.message_handler(commands=['reset'])
def reset_handler(message):
    chats_history[message.chat.id] = [{"role": "system", "content": MY_BRIEF}]
    bot.reply_to(message, "Брат, я всё забыл! Начинаем с чистого листа.")

@bot.message_handler(func=lambda m: True)
def chat_handler(message):
    user_id = message.chat.id
    if user_id not in chats_history:
        chats_history[user_id] = [{"role": "system", "content": MY_BRIEF}]
    
    chats_history[user_id].append({"role": "user", "content": message.text})
    
    # ПРАВИЛЬНАЯ обрезка истории (оставляем системный промпт + 8 последних сообщений)
    if len(chats_history[user_id]) > 10:
        chats_history[user_id] = [chats_history[user_id][0]] + chats_history[user_id][-8:]
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chats_history[user_id],
            temperature=0.7,
            max_tokens=2000,
        )
        answer = completion.choices[0].message.content # Исправил индекс тут
        chats_history[user_id].append({"role": "assistant", "content": answer})
        
        try:
            bot.send_message(user_id, answer, parse_mode="Markdown")
        except:
            bot.send_message(user_id, answer)
            
    except Exception as e:
        print(f"Ошибка в чате: {e}")
        bot.send_message(user_id, "Брат, чёт я подвис. Дай мне секунду.")

# --- УСИЛЕННЫЙ ЗАПУСК ---
def start_bot():
    print(">>> Кент выходит на связь...")
    while True:
        try:
            # infinity_polling сам пытается переподключиться при обрыве сети
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Критическая ошибка: {e}. Рестарт через 5 сек...")
            time.sleep(5)

if name == "main":
    threading.Thread(target=run_flask).start()
    start_bot()
