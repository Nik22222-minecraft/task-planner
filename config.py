import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Секретный ключ (для GitHub можно оставить любой тестовый)
    SECRET_KEY = 'super-secret-key-change-me'
    
    # Путь к базе данных (с тайм-аутом от блокировок)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'database.db') + '?timeout=30'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ВАЖНО: Удали свой реальный токен перед коммитом!
    BOT_TOKEN = 'ТВОЙ_ТОКЕН_ОТ_БОТФАЗЕРА'
