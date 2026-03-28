from flask import Flask, request
from config import Config
from models import db, User, Task
from routes import main
from bot import TaskBotApp
from datetime import datetime, timedelta

# 1. Инициализация приложения Flask
app = Flask(__name__)
app.config.from_object(Config)

# 2. Подключение базы данных
db.init_app(app)

with app.app_context():
    db.create_all()

# 3. Регистрация маршрутов
app.register_blueprint(main)

# 4. Инициализация Telegram-бота
my_bot = TaskBotApp(Config.BOT_TOKEN, app)

# === НОВАЯ СИСТЕМА НАПОМИНАНИЙ (БЕЗ ОШИБОК БАЗЫ) ===
reminded_tasks = set()
last_clear_day = datetime.utcnow().day

@app.route('/secret_ping_reminders')
def secret_ping_reminders():
    global reminded_tasks, last_clear_day

    current_utc_day = datetime.utcnow().day
    if current_utc_day != last_clear_day:
        reminded_tasks.clear()
        last_clear_day = current_utc_day

    users = User.query.filter(User.telegram_id != None).all()
    for user in users:
        user_now = datetime.utcnow() + timedelta(hours=user.timezone)
        user_date = user_now.strftime('%Y-%m-%d')
        user_time = user_now.strftime('%H:%M')

        # МАГИЯ ЗДЕСЬ: time_start <= user_time (даже если сервер лагнет, он не пропустит задачу)
        tasks = Task.query.filter(
            Task.user_id == user.id,
            Task.date == user_date,
            Task.time_start != "",
            Task.time_start <= user_time,
            Task.completed == False
        ).all()

        for t in tasks:
            if t.id not in reminded_tasks:
                try:
                    my_bot.bot.send_message(
                        user.telegram_id,
                        f"⏰ <b>НАПОМИНАНИЕ!</b>\n\nПора заняться задачей:\n👉 <b>{t.content}</b>\n\n<i>Важность: {t.priority}</i>",
                        parse_mode="HTML"
                    )
                    reminded_tasks.add(t.id)
                except:
                    pass
    return "OK"
# ====================================================

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
