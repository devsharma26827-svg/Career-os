import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///./"):
    # Anchor relative SQLite path to the backend root directory for consistency
    backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    rel_db_file = db_url.replace("sqlite:///./", "")
    abs_db_path = os.path.abspath(os.path.join(backend_root, rel_db_file)).replace("\\", "/")
    db_url = f"sqlite:///{abs_db_path}"

# For SQLite, check_same_thread=False is needed
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
