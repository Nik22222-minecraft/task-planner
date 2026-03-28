import time
from datetime import datetime
from app import app, my_bot
from models import db, Task, User

print("🚀 Система напоминаний NikPlay запущена!")
reminded_tasks = set()

while True:
    try:
        with app.app_context():
            now = datetime.now()
            current_date = now.strftime('%Y-%m-%d')
            current_time = now.strftime('%H:%M')
            
            if current_time == "00:00":
                reminded_tasks.clear()
                
            tasks = Task.query.filter_by(date=current_date, time_start=current_time, completed=False).all()
            
            for t in tasks:
                if t.id not in reminded_tasks:
                    user = User.query.get(t.user_id)
                    if user and user.telegram_id:
                        try:
                            my_bot.bot.send_message(
                                user.telegram_id,
                                f"⏰ <b>НАПОМИНАНИЕ!</b>\n\nПора заняться задачей:\n👉 <b>{t.content}</b>\n\n<i>Важность: {t.priority}</i>",
                                parse_mode="HTML"
                            )
                            reminded_tasks.add(t.id)
                            print(f"[{current_time}] Уведомление отправлено для задачи #{t.id}")
                        except Exception as e:
                            pass
    except Exception as e:
        print(f"Ошибка доступа к БД (ждем...): {e}")
        
    time.sleep(30) # Ждем 30 секунд перед следующей проверкой
