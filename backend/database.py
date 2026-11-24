import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Define the user home directory path for storing data
HOME_DIR = os.path.expanduser("~")
APP_DIR = os.path.join(HOME_DIR, ".face-nexa")
DB_PATH = os.path.join(APP_DIR, "facenexa.db")

# Ensure the application directory exists
os.makedirs(APP_DIR, exist_ok=True)
os.makedirs(os.path.join(APP_DIR, "students"), exist_ok=True)
os.makedirs(os.path.join(APP_DIR, "attendance"), exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
