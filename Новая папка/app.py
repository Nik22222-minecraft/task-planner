from flask import Flask, request
from config import Config
from models import db
from routes import main
from bot import TaskBotApp

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