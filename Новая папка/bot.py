import telebot
from datetime import datetime
import os
from werkzeug.security import check_password_hash

# Импортируем модели, чтобы бот мог работать с БД
from models import db, User, Task

class TaskBotApp:
    """Класс для управления Telegram-ботом."""
    
    def __init__(self, token, flask_app):
        self.bot = telebot.TeleBot(token, threaded=False)
        self.app = flask_app
        self.basedir = os.path.abspath(os.path.dirname(__file__))
        self.setup_handlers()

    def setup_handlers(self):
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            text = (
                "Привет! Я бот-помощник сайта NikPlay! 🤖\n\n"
                "🔒 <b>Безопасность:</b> Чтобы я показал твои задачи, сначала привяжи аккаунт:\n"
                "/login [твой_логин] [твой_пароль]\n\n"
                "📌 <b>Мои команды:</b>\n"
                "/tasks — посмотреть мои задачи на сегодня\n"
                "/add [текст] — добавить новую задачу на сегодня\n"
                "/del [номер] — удалить задачу\n"
                "/feedback [текст] — оценить сайт\n"
                "/report [текст] — сообщить об ошибке\n"
                "/help — показать это меню"
            )
            self.bot.reply_to(message, text, parse_mode="HTML")

        @self.bot.message_handler(commands=['login'])
        def login_user(message):
            parts = message.text.split()
            if len(parts) != 3:
                self.bot.reply_to(message, "⚠️ Ошибка! Пиши так:\n/login ТвойЛогин ТвойПароль")
                return
            
            username, password = parts[1], parts[2]
            
            with self.app.app_context():
                user = User.query.filter_by(username=username).first()
                if user and check_password_hash(user.password, password):
                    user.telegram_id = str(message.from_user.id)
                    db.session.commit()
                    self.bot.reply_to(
                        message, 
                        f"✅ Аккаунт <b>{username}</b> привязан! Пиши /tasks", 
                        parse_mode="HTML"
                    )
                else:
                    self.bot.reply_to(message, "❌ Неверный логин или пароль.")

        @self.bot.message_handler(commands=['tasks'])
        def get_today_tasks(message):
            with self.app.app_context():
                user = User.query.filter_by(telegram_id=str(message.from_user.id)).first()
                
                if not user:
                    self.bot.reply_to(message, "⚠️ Сначала привяжи аккаунт: /login логин пароль")
                    return
                
                today = datetime.now().strftime('%Y-%m-%d')
                tasks = Task.query.filter_by(user_id=user.id, date=today).all()
                
                if not tasks:
                    self.bot.reply_to(message, "На сегодня задач нет! Можно отдыхать! 🌴\n\nДобавить задачу: /add [текст]")
                    return
                
                resp = f"📝 Твои задачи на сегодня ({today}):\n\n"
                for t in tasks:
                    status = "✅" if t.completed else "⬜"
                    time_str = t.time_start if t.time_start else "Весь день"
                    # Добавили вывод ID задачи для удобного удаления
                    resp += f"🆔 {t.id} | {status} [{t.priority}] {t.content} (Время: {time_str})\n"
                
                resp += "\n💡 Чтобы удалить задачу, напиши /del [номер]"
                self.bot.reply_to(message, resp)

        @self.bot.message_handler(commands=['add'])
        def add_task(message):
            parts = message.text.split(maxsplit=1)
            if len(parts) < 2:
                self.bot.reply_to(message, "⚠️ Напиши текст задачи после команды.\nПример: /add Сделать домашку по алгебре")
                return
            
            task_text = parts[1]
            
            with self.app.app_context():
                user = User.query.filter_by(telegram_id=str(message.from_user.id)).first()
                if not user:
                    self.bot.reply_to(message, "⚠️ Сначала привяжи аккаунт: /login логин пароль")
                    return
                
                today = datetime.now().strftime('%Y-%m-%d')
                # Создаем задачу по умолчанию (Средняя важность, без времени)
                new_task = Task(
                    content=task_text,
                    category='Общее',
                    priority='Средняя',
                    date=today,
                    user_id=user.id
                )
                db.session.add(new_task)
                db.session.commit()
                
                self.bot.reply_to(message, f"✅ Задача успешно добавлена на сегодня:\n«{task_text}»\n\nПиши /tasks чтобы посмотреть список.")

        @self.bot.message_handler(commands=['del', 'delete'])
        def delete_task(message):
            parts = message.text.split(maxsplit=1)
            # Проверяем, что ввели команду и число (ID)
            if len(parts) < 2 or not parts[1].isdigit():
                self.bot.reply_to(message, "⚠️ Укажи ID задачи цифрой.\nПосмотри ID через /tasks и напиши, например: /del 5")
                return
            
            task_id = int(parts[1])
            
            with self.app.app_context():
                user = User.query.filter_by(telegram_id=str(message.from_user.id)).first()
                if not user:
                    self.bot.reply_to(message, "⚠️ Сначала привяжи аккаунт: /login логин пароль")
                    return
                
                task = Task.query.get(task_id)
                
                # Важная проверка безопасности: существует ли задача и принадлежит ли она этому пользователю
                if task and task.user_id == user.id:
                    db.session.delete(task)
                    db.session.commit()
                    self.bot.reply_to(message, f"🗑️ Задача 🆔 {task_id} удалена!")
                else:
                    self.bot.reply_to(message, "❌ Ошибка: задача не найдена или принадлежит не тебе.")

        @self.bot.message_handler(commands=['feedback'])
        def receive_feedback(message):
            parts = message.text.split(maxsplit=1)
            if len(parts) < 2:
                self.bot.reply_to(message, "⚠️ Напиши отзыв после команды. Пример: /feedback Супер!")
                return
                
            filepath = os.path.join(self.basedir, 'feedback.txt')
            with open(filepath, 'a', encoding='utf-8') as f:
                time_now = datetime.now().strftime('%Y-%m-%d %H:%M')
                f.write(f"[{time_now}] От @{message.from_user.username}: {parts[1]}\n")
                
            self.bot.reply_to(message, "Спасибо за оценку! 💖")

        @self.bot.message_handler(commands=['report'])
        def receive_report(message):
            parts = message.text.split(maxsplit=1)
            if len(parts) < 2:
                self.bot.reply_to(message, "⚠️ Опиши проблему. Пример: /report Сайт зависает")
                return
                
            filepath = os.path.join(self.basedir, 'reports.txt')
            with open(filepath, 'a', encoding='utf-8') as f:
                time_now = datetime.now().strftime('%Y-%m-%d %H:%M')
                f.write(f"[{time_now}] АЛАРМ от @{message.from_user.username}: {parts[1]}\n")
                
            self.bot.reply_to(message, "🚨 Ошибка отправлена. Разработчик уже бежит чинить!")

        @self.bot.message_handler(func=lambda message: True)
        def echo_all(message):
            self.bot.reply_to(message, "Я понимаю только команды. Нажми /help!")

    def process_new_update(self, json_string):
        update = telebot.types.Update.de_json(json_string)
        self.bot.process_new_updates([update])