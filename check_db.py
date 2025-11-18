import sqlite3
import os

# Путь к настоящей базе
DB_PATH = os.path.join("instance", "users.db")
print("DB_PATH:", DB_PATH)

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

try:
    c.execute("SELECT id, nombre, image_key FROM course")
    rows = c.fetchall()
    print("Cursos en la base:")
    for row in rows:
        print(row)

except Exception as e:
    print("ERROR:", e)

conn.close()