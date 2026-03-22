from flask_sqlalchemy import SQLAlchemy

# Инициализируем объект базы данных (без привязки к приложению)
db = SQLAlchemy()

class User(db.Model):
    """Модель пользователя системы."""
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    theme = db.Column(db.String(20), default='purple')
    telegram_id = db.Column(db.String(100), nullable=True)
    is_public = db.Column(db.Boolean, default=False)
    
    # Связь с задачами (Один ко многим)
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
    
    # Внешний ключ, указывающий на владельца задачи
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)