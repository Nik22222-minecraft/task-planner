from flask import Flask, request
from config import Config
from models import db, Task, User
from routes import main
from bot import TaskBotApp
import threading
import time
from datetime import datetime

# 1. Инициализация приложения Flask
app = Flask(__name__)
app.config.from_object(Config)

# 2. Подключение базы данных
db.init_app(app)

with app.app_context():
    db.create_all()

# 3. Регистрация маршрутов (Blueprints)
app.register_blueprint(main)

# 4. Инициализация Telegram-бота
my_bot = TaskBotApp(Config.BOT_TOKEN, app)

# === НОВАЯ ФИЧА: ФОНОВЫЕ НАПОМИНАНИЯ ===
def reminder_loop(flask_app, bot_instance):
    """Фоновый поток, который проверяет задачи каждую минуту и шлет уведомления"""
    reminded_tasks = set() # Память о том, кому уже напомнили, чтобы не спамить
    
    while True:
        try:
            with flask_app.app_context():
                now = datetime.now()
                current_date = now.strftime('%Y-%m-%d')
                current_time = now.strftime('%H:%M') # Формат времени как в базе (например, 14:30)
                
                # В полночь очищаем память отправленных уведомлений
                if current_time == "00:00":
                    reminded_tasks.clear()
                    
                # Ищем невыполненные задачи на сегодня, у которых время совпало с текущим
                tasks = Task.query.filter_by(date=current_date, time_start=current_time, completed=False).all()
                
                for t in tasks:
                    if t.id not in reminded_tasks:
                        user = User.query.get(t.user_id)
                        if user and user.telegram_id:
                            try:
                                # Отправляем пуш-уведомление в Telegram
                                bot_instance.send_message(
                                    user.telegram_id,
                                    f"⏰ <b>НАПОМИНАНИЕ!</b>\n\nПора заняться задачей:\n👉 <b>{t.content}</b>\n\n<i>Важность: {t.priority}</i>",
                                    parse_mode="HTML"
                                )
                                reminded_tasks.add(t.id) # Запоминаем, что уже отправили
                            except Exception as e:
                                print(f"Ошибка отправки напоминания: {e}")
        except Exception as e:
            print(f"Ошибка в цикле напоминаний: {e}")
            
        time.sleep(30) # Проверяем время каждые 30 секунд

# Запускаем фоновый поток при старте сервера
threading.Thread(target=reminder_loop, args=(app, my_bot.bot), daemon=True).start()
# =======================================

# 5. Маршрут для Webhook Telegram-бота
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        my_bot.process_new_update(json_string)
        return ''
    else:
        return 'error'

if __name__ == '__main__':
    app.run(debug=True)