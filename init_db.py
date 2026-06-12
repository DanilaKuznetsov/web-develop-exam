import pymysql

# Конфигурация
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = '1234'
DB_NAME = 'library_db'

try:
    print("Подключение к MySQL...")
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = connection.cursor()
    print("Создание базы данных (если не существует)...")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    connection.commit()
    print("База данных успешно создана!")
    
    # Теперь подключаемся к созданной базе
    connection.select_db(DB_NAME)
    
    print("Всё отлично! База данных готова.")
except Exception as e:
    print(f"Ошибка: {e}")
finally:
    if 'connection' in locals() and connection.open:
        connection.close()
