"""
Simple SQLite auth + search history storage.
Passwords are hashed (pbkdf2_sha256); never store plain text.
"""

import os
from pathlib import Path

from passlib.hash import pbkdf2_sha256
from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# AUTH_DB_PATH lets Docker/Kubernetes keep the database on a persistent volume.
# Without it, the database stays next to the project exactly as before.
DB_PATH = Path(os.environ.get("AUTH_DB_PATH") or Path(__file__).parent.parent / "auth.db")
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, future=True)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)


class SearchHistory(Base):
    __tablename__ = "search_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    symbol = Column(String, nullable=False)
    date_range = Column(String, nullable=False)
    strategy = Column(String, nullable=False)
    action = Column(String, nullable=True)  # Buy / Sell / N/A
    # price column removed per user request
    timestamp = Column(String, nullable=False)


def init_db() -> None:
    Base.metadata.create_all(engine)


def create_user(username: str, password: str) -> None:
    with SessionLocal() as session:
        if session.query(User).filter_by(username=username).first():
            raise ValueError("User already exists")
        user = User(username=username, password_hash=pbkdf2_sha256.hash(password))
        session.add(user)
        session.commit()


def verify_user(username: str, password: str) -> bool:
    with SessionLocal() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return False
        return pbkdf2_sha256.verify(password, user.password_hash)


def add_search(
    username: str,
    symbol: str,
    date_range: str,
    strategy: str,
    timestamp: str,
    action: str | None = None,
) -> None:
    with SessionLocal() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return
        rec = SearchHistory(
            user_id=user.id,
            symbol=symbol,
            date_range=date_range,
            strategy=strategy,
            action=action,
            timestamp=timestamp,
        )
        session.add(rec)
        session.commit()


def get_searches(username: str, limit: int = 10):
    with SessionLocal() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return []
        q = (
            session.query(SearchHistory)
            .filter_by(user_id=user.id)
            .order_by(SearchHistory.id.desc())
            .limit(limit)
        )
        return [
            {
                "symbol": r.symbol,
                "date_range": r.date_range,
                "strategy": r.strategy,
                "timestamp": r.timestamp,
                "action": r.action,
            }
            for r in q
        ]


if __name__ == "__main__":
    init_db()
    print(f"DB initialized at {DB_PATH}")
