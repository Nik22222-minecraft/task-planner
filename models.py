from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    """Модель пользователя системы."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    theme = db.Column(db.String(20), default='purple')
    telegram_id = db.Column(db.String(100), nullable=True)
    is_public = db.Column(db.Boolean, default=False)
    
    # НОВОЕ ПОЛЕ: Часовой пояс пользователя (по умолчанию UTC+3, Москва)
    timezone = db.Column(db.Integer, default=3)
    
    tasks = db.relationship('Task', backref='owner', lazy=True)


class Task(db.Model):
    """Модель задачи в планировщике."""
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
