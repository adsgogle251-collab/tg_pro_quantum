"""TG PRO QUANTUM - Database Manager"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
from pathlib import Path
from datetime import datetime
from .utils import DATA_DIR, log, log_error

Base = declarative_base()
DATABASE_PATH = DATA_DIR / "database.db"

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=False)
    level = Column(Integer, default=1)
    status = Column(String(50), default='active')
    created_at = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._init_db()

    def _init_db(self):
        try:
            DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.engine = create_engine(f"sqlite:///{DATABASE_PATH}", echo=False, connect_args={"check_same_thread": False}, poolclass=StaticPool)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            Base.metadata.create_all(bind=self.engine)
            log("Database initialized", "success")
        except Exception as e:
            log_error(f"Database init failed: {e}")
            raise

    def get_session(self): return self.SessionLocal()

db_manager = DatabaseManager()
__all__ = ["Base", "Account", "DatabaseManager", "db_manager"]