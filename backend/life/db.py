import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Base(DeclarativeBase):
    pass

def make_engine(url):
    engine = create_engine(url, pool_pre_ping=True,
        connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def sqlite_setup(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=5000")
    return engine

engine = make_engine(os.getenv("DATABASE_URL", "sqlite:///./life.db"))
Session = sessionmaker(engine, expire_on_commit=False)

def session():
    with Session() as db:
        yield db
