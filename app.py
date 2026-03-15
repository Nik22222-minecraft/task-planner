from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash # ЗАЩИТА ПАРОЛЕЙ
from datetime import datetime, timedelta
import os
import telebot

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ТВОЙ_СЕКРЕТНЫЙ_КЛЮЧ'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
db = SQLAlchemy(app)

# === БАЗА ДАННЫХ ===
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False) # Увеличили для хеша
    theme = db.Column(db.String(20), default='purple')
    telegram_id = db.Column(db.String(100), nullable=True)
    is_public = db.Column(db.Boolean, default=False)
    tasks = db.relationship('Task', backref='owner', lazy=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), default='Общее')
    priority = db.Column(db.String(20), nullable=False)
    time_start = db.Column(db.String(10))
    time_end = db.Column(db.String(10))
    description = db.Column(db.Text, default="")
    date = db.Column(db.String(10), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

with app.app_context():
    db.create_all()

def cleanup_old_tasks(user_id):
    limit = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    Task.query.filter(Task.user_id == user_id, Task.date < limit).delete()
    db.session.commit()

# === ООП-КЛАСС ДЛЯ БОТА ===
class TaskBotApp:
    def __init__(self, token, flask_app, database, user_model, task_model):
        self.bot = telebot.TeleBot(token, threaded=False)
        self.app = flask_app
        self.db = database
        self.User = user_model
        self.Task = task_model
        self.setup_handlers()

    def setup_handlers(self):
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            # Используем HTML для безопасного красивого шрифта
            text = (
                "Привет! Я бот-помощник сайта NikPlay! 🤖\n\n"
                "🔒 <b>Безопасность:</b> Чтобы я показал твои задачи, сначала привяжи аккаунт:\n"
                "/login [твой_логин] [твой_пароль]\n\n"
                "📌 <b>Мои команды:</b>\n"
                "/tasks — посмотреть мои задачи на сегодня\n"
                "/feedback [текст] — оценить сайт или оставить отзыв\n"
                "/report [текст] — сообщить, если сайт сломался или завис\n"
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
                user = self.User.query.filter_by(username=username).first()
                # Проверяем пароль через ХЕШ
                if user and check_password_hash(user.password, password):
                    user.telegram_id = str(message.from_user.id)
                    self.db.session.commit()
                    self.bot.reply_to(message, f"✅ Аккаунт <b>{username}</b> успешно привязан! Теперь твои задачи под защитой. Пиши /tasks", parse_mode="HTML")
                else:
                    self.bot.reply_to(message, "❌ Неверный логин или пароль. Проверь данные с сайта.")

        @self.bot.message_handler(commands=['tasks'])
        def get_today_tasks(message):
            with self.app.app_context():
                user = self.User.query.filter_by(telegram_id=str(message.from_user.id)).first()
                if not user:
                    self.bot.reply_to(message, "⚠️ Сначала привяжи аккаунт командой:\n/login логин пароль")
                    return
                
                today = datetime.now().strftime('%Y-%m-%d')
                tasks = self.Task.query.filter_by(user_id=user.id, date=today).all()
                
                if not tasks:
                    self.bot.reply_to(message, "На сегодня задач нет! Можно отдыхать! 🌴")
                    return
                
                resp = f"📝 Твои задачи на сегодня ({today}):\n\n"
                for t in tasks:
                    status = "✅" if t.completed else "⬜"
                    time_str = t.time_start if t.time_start else "Весь день"
                    resp += f"{status} [{t.priority}] {t.content} (Время: {time_str})\n"
                
                self.bot.reply_to(message, resp)

        @self.bot.message_handler(commands=['feedback'])
        def receive_feedback(message):
            parts = message.text.split(maxsplit=1)
            if len(parts) < 2:
                self.bot.reply_to(message, "⚠️ Напиши свой отзыв после команды.\nПример: /feedback Бот просто супер!")
                return
            with open(os.path.join(basedir, 'feedback.txt'), 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] От @{message.from_user.username}: {parts[1]}\n")
            self.bot.reply_to(message, "Спасибо за оценку! 💖 Мы становимся лучше благодаря тебе.")

        @self.bot.message_handler(commands=['report'])
        def receive_report(message):
            parts = message.text.split(maxsplit=1)
            if len(parts) < 2:
                self.bot.reply_to(message, "⚠️ Опиши проблему.\nПример: /report Сайт зависает при добавлении задачи")
                return
            with open(os.path.join(basedir, 'reports.txt'), 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] АЛАРМ от @{message.from_user.username}: {parts[1]}\n")
            self.bot.reply_to(message, "🚨 Сообщение об ошибке отправлено техподдержке. Разработчик NikPlay уже бежит чинить сервер!")

        @self.bot.message_handler(func=lambda message: True)
        def echo_all(message):
            self.bot.reply_to(message, "Я понимаю только команды. Нажми /help чтобы посмотреть меню!")

    def process_new_update(self, json_string):
        update = telebot.types.Update.de_json(json_string)
        self.bot.process_new_updates([update])

# === ИНИЦИАЛИЗАЦИЯ БОТА (С ИСПРАВЛЕННЫМ ТОКЕНОМ) ===
TOKEN = 'ТВОЙ_ТОКЕН_ОТ_BOTFATHER'
my_bot = TaskBotApp(TOKEN, app, db, User, Task)

# === МАРШРУТЫ САЙТА И ВЕБХУК ===
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        my_bot.process_new_update(json_string)
        return ''
    else:
        return 'error'

@app.route('/community')
def community():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    today = datetime.now().strftime('%Y-%m-%d')
    public_users = User.query.filter_by(is_public=True).all()
    
    community_data = []
    for pu in public_users:
        tasks = Task.query.filter_by(user_id=pu.id, date=today).all()
        community_data.append({'username': pu.username, 'tasks': tasks})
        
    return render_template('community.html', user=user, community_data=community_data, today=today)

@app.route('/toggle_public')
def toggle_public():
    if 'user_id' not in session: return redirect(url_for('login'))
    u = User.query.get(session['user_id'])
    u.is_public = not u.is_public
    db.session.commit()
    return redirect(request.referrer)

@app.route('/tasks/<date>')
def view_tasks(date):
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if not user: return redirect(url_for('logout'))
    cleanup_old_tasks(user.id)
    sort_mode = request.args.get('sort', 'priority')
    selected_cat = request.args.get('category', 'Все')
    query = Task.query.filter_by(user_id=user.id, date=date)
    if selected_cat != 'Все': query = query.filter_by(category=selected_cat)
    prio_order = db.case({"Высокая": 1, "Средняя": 2, "Низкая": 3}, value=Task.priority)
    if sort_mode == 'time':
        tasks = query.order_by(Task.time_start == "", Task.time_start, prio_order).all()
    else:
        tasks = query.order_by(prio_order, Task.time_start == "", Task.time_start).all()
    cats = [c[0] for c in db.session.query(Task.category).filter_by(user_id=user.id).distinct().all()]
    return render_template('tasks.html', tasks=tasks, current_date=date, user=user, categories=cats, selected_cat=selected_cat, sort_mode=sort_mode)

@app.route('/add_task', methods=['POST'])
def add_task():
    d = request.form
    start_dt = datetime.strptime(d['date'], '%Y-%m-%d')
    db.session.add(Task(content=d['content'], category=d['category'] or 'Общее', priority=d['priority'], 
                        time_start=d['time_start'], time_end=d['time_end'], date=d['date'], user_id=session['user_id']))
    re_days = request.form.getlist('repeat_days')
    re_weeks = d.get('repeat_count', type=int) or 0
    if re_days and re_weeks > 0:
        for w in range(re_weeks + 1):
            for day in range(7):
                curr = start_dt + timedelta(weeks=w, days=day)
                if w == 0 and curr <= start_dt: continue
                if str(curr.weekday()) in re_days:
                    db.session.add(Task(content=d['content'], category=d['category'] or 'Общее', priority=d['priority'],
                                        time_start=d['time_start'], time_end=d['time_end'], date=curr.strftime('%Y-%m-%d'), user_id=session['user_id']))
    db.session.commit()
    return redirect(url_for('view_tasks', date=d['date']))

@app.route('/edit_task/<int:task_id>', methods=['POST'])
def edit_task(task_id):
    t = Task.query.get(task_id)
    if t and t.user_id == session.get('user_id'):
        t.content = request.form.get('content')
        t.priority = request.form.get('priority')
        db.session.commit()
    return redirect(request.referrer)

@app.route('/update_note_action/<int:task_id>', methods=['POST'])
def update_note_action(task_id):
    t = Task.query.get(task_id)
    act = request.form.get('action')
    note = request.form.get('note')
    if t and t.user_id == session.get('user_id'):
        if act == 'only_this': t.description = note
        elif act == 'future_tasks':
            for ft in Task.query.filter(Task.user_id==t.user_id, Task.content==t.content, Task.date>=t.date).all(): ft.description = note
        elif act == 'category_all':
            for ct in Task.query.filter(Task.user_id==t.user_id, Task.category==t.category).all(): ct.description = note
        db.session.commit()
    return redirect(request.referrer)

@app.route('/toggle/<int:task_id>')
def toggle_task(task_id):
    t = Task.query.get(task_id); t.completed = not t.completed; db.session.commit()
    return redirect(request.referrer)

@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    t = Task.query.get(task_id); db.session.delete(t); db.session.commit()
    return redirect(request.referrer)

@app.route('/change_theme/<theme_name>')
def change_theme(theme_name):
    u = User.query.get(session.get('user_id')); u.theme = theme_name; db.session.commit()
    return redirect(request.referrer)

# АВТОРИЗАЦИЯ С ХЕШИРОВАНИЕМ
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
    return render_template('login.html')

# РЕГИСТРАЦИЯ С ХЕШИРОВАНИЕМ
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'])
        new_user = User(username=request.form['username'], password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/')
def index():
    if 'user_id' not in session: return redirect(url_for('login'))
    return redirect(url_for('view_tasks', date=datetime.now().strftime('%Y-%m-%d')))

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

if __name__ == '__main__': app.run(debug=True)