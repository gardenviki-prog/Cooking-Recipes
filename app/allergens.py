
import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE ingredients ADD COLUMN allergen_tags TEXT DEFAULT ''")
    print("Колонку allergen_tags додано.")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e):
        print("Колонка вже існує, пропускаємо.")
    else:
        raise

conn.commit()
conn.close()
print("Готово.")
