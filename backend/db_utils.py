# backend/db_utils.py
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=False, future=True)

def get_faculty_count(department: str):
    with engine.connect() as conn:
        r = conn.execute(text("SELECT COUNT(*) FROM faculty WHERE lower(department)=lower(:d)"), {"d": department})
        return r.scalar() or 0

# Add more helpers as needed (insert, update, search)
def add_faculty(name: str, department: str, email: str):
    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO faculty (name, department, email) VALUES (:n, :d, :e)"),
            {"n": name, "d": department, "e": email}
        )
        conn.commit()
def find_faculty_by_email(email: str):
    with engine.connect() as conn:
        r = conn.execute(
            text("SELECT * FROM faculty WHERE email=:e"),
            {"e": email}
        )
        return r.fetchone()
# ...existing code...
