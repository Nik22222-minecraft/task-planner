import time
import urllib.request

print("🚀 Пингатор (HTTP-демон) NikPlay запущен! Никаких ошибок БД больше не будет.")

while True:
    try:
        # Скрипт просто "дергает" тайный адрес твоего сайта каждые 30 секунд
        urllib.request.urlopen("https://nikplay4ik.pythonanywhere.com/secret_ping_reminders")
    except Exception as e:
        pass
    
    time.sleep(30)
