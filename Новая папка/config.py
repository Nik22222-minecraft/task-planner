import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Секретный ключ (для GitHub можно оставить любой тестовый)
    SECRET_KEY = 'super-secret-key-change-me'
    
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ВАЖНО: Удали свой реальный токен перед коммитом!
    BOT_TOKEN = 'ТВОЙ_ТОКЕН_ОТ_БОТФАЗЕРА'