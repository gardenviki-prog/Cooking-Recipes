from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS allergen_tags TEXT DEFAULT ''"))
    conn.commit()

print("Done")
