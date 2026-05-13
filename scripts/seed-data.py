import uuid
import json
import psycopg2
from datetime import datetime, timedelta

def seed_db():
    conn = psycopg2.connect("postgresql://postgres_user:postgres_password@localhost:5432/shieldcloud")
    cur = conn.cursor()
    # Seed users
    admin_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    cur.execute("""
        INSERT INTO users (id, email, password_hash, role)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (admin_id, 'admin@shieldcloud.local', 'hashed_pass', 'admin'))

    cur.execute("""
        INSERT INTO users (id, email, password_hash, role)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (user_id, 'user@shieldcloud.local', 'hashed_pass', 'user'))

    conn.commit()
    cur.close()
    conn.close()
    print("Database seeded successfully.")

if __name__ == "__main__":
    seed_db()
