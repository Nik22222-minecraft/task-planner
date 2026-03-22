from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

from models import db, User, Task

# Создаем "чертеж" для наших маршрутов
main = Blueprint('main', __name__)

def cleanup_old_tasks(user_id):
    """Удаляет задачи пользователя старше 7 дней."""
    limit = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    Task.query.filter(Task.user_id == user_id, Task.date < limit).delete()
    db.session.commit()

# === АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ ===

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('main.index'))
    # Теперь мы используем один шаблон для логина и регистрации!
    return render_template('auth.html')

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'])
        new_user = User(username=request.form['username'], password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('main.login'))
    return render_template('auth.html')

@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))

# === ОСНОВНЫЕ МАРШРУТЫ ===

@main.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
        
    today = datetime.now().strftime('%Y-%m-%d')
    return redirect(url_for('main.view_tasks', date=today))

@main.route('/tasks/<date>')
def view_tasks(date):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
        
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('main.logout'))
        
    cleanup_old_tasks(user.id)
    
    sort_mode = request.args.get('sort', 'priority')
    selected_cat = request.args.get('category', 'Все')
    
    query = Task.query.filter_by(user_id=user.id, date=date)
    if selected_cat != 'Все':
        query = query.filter_by(category=selected_cat)
        
    prio_order = db.case({"Высокая": 1, "Средняя": 2, "Низкая": 3}, value=Task.priority)
    
    if sort_mode == 'time':
        tasks = query.order_by(Task.time_start == "", Task.time_start, prio_order).all()
    else:
        tasks = query.order_by(prio_order, Task.time_start == "", Task.time_start).all()
        
    cats_data = db.session.query(Task.category).filter_by(user_id=user.id).distinct().all()
    cats = [c[0] for c in cats_data]
    
    return render_template('tasks.html', 
                           tasks=tasks, 
                           current_date=date, 
                           user=user, 
                           categories=cats, 
                           selected_cat=selected_cat, 
                           sort_mode=sort_mode)

@main.route('/add_task', methods=['POST'])
def add_task():
    d = request.form
    start_dt = datetime.strptime(d['date'], '%Y-%m-%d')
    
    new_task = Task(
        content=d['content'],
        category=d['category'] or 'Общее',
        priority=d['priority'],
        time_start=d['time_start'],
        time_end=d['time_end'],
        date=d['date'],
        user_id=session['user_id']
    )
    db.session.add(new_task)
    
    re_days = request.form.getlist('repeat_days')
    re_weeks = d.get('repeat_count', type=int) or 0
    
    if re_days and re_weeks > 0:
        for w in range(re_weeks + 1):
            for day in range(7):
                curr = start_dt + timedelta(weeks=w, days=day)
                if w == 0 and curr <= start_dt:
                    continue
                if str(curr.weekday()) in re_days:
                    repeat_task = Task(
                        content=d['content'],
                        category=d['category'] or 'Общее',
                        priority=d['priority'],
                        time_start=d['time_start'],
                        time_end=d['time_end'],
                        date=curr.strftime('%Y-%m-%d'),
                        user_id=session['user_id']
                    )
                    db.session.add(repeat_task)
                    
    db.session.commit()
    return redirect(url_for('main.view_tasks', date=d['date']))

# === РЕДАКТИРОВАНИЕ И УДАЛЕНИЕ ===

@main.route('/edit_task/<int:task_id>', methods=['POST'])
def edit_task(task_id):
    t = Task.query.get(task_id)
    if t and t.user_id == session.get('user_id'):
        t.content = request.form.get('content')
        t.priority = request.form.get('priority')
        db.session.commit()
    return redirect(request.referrer)

@main.route('/update_note_action/<int:task_id>', methods=['POST'])
def update_note_action(task_id):
    t = Task.query.get(task_id)
    act = request.form.get('action')
    note = request.form.get('note')
    
    if t and t.user_id == session.get('user_id'):
        if act == 'only_this':
            t.description = note
        elif act == 'future_tasks':
            future_tasks = Task.query.filter(
                Task.user_id == t.user_id, 
                Task.content == t.content, 
                Task.date >= t.date
            ).all()
            for ft in future_tasks:
                ft.description = note
        elif act == 'category_all':
            cat_tasks = Task.query.filter(
                Task.user_id == t.user_id, 
                Task.category == t.category
            ).all()
            for ct in cat_tasks:
                ct.description = note
        db.session.commit()
        
    return redirect(request.referrer)

@main.route('/toggle/<int:task_id>')
def toggle_task(task_id):
    t = Task.query.get(task_id)
    if t and t.user_id == session.get('user_id'):
        t.completed = not t.completed
        db.session.commit()
    return redirect(request.referrer)

@main.route('/delete/<int:task_id>')
def delete_task(task_id):
    t = Task.query.get(task_id)
    if t and t.user_id == session.get('user_id'):
        db.session.delete(t)
        db.session.commit()
    return redirect(request.referrer)

# === ДОП ФУНКЦИИ ===

@main.route('/change_theme/<theme_name>')
def change_theme(theme_name):
    user = User.query.get(session.get('user_id'))
    if user:
        user.theme = theme_name
        db.session.commit()
    return redirect(request.referrer)

@main.route('/community')
def community():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
        
    user = User.query.get(session['user_id'])
    today = datetime.now().strftime('%Y-%m-%d')
    public_users = User.query.filter_by(is_public=True).all()
    
    community_data = []
    for pu in public_users:
        tasks = Task.query.filter_by(user_id=pu.id, date=today).all()
        community_data.append({'username': pu.username, 'tasks': tasks})
        
    return render_template('community.html', user=user, community_data=community_data, today=today)

@main.route('/toggle_public')
def toggle_public():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
        
    user = User.query.get(session['user_id'])
    if user:
        user.is_public = not user.is_public
        db.session.commit()
        
    return redirect(request.referrer)