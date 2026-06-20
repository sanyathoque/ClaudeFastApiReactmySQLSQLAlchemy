import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Connection string for the MySQL database.
# Format: mysql+pymysql://<user>:<password>@<host>:<port>/<database>
# Override it with the DATABASE_URL environment variable (see .env.example).
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:password@localhost:3306/fastapi_db",
)

# pool_pre_ping checks a connection is still alive before using it, which
# avoids "MySQL server has gone away" errors on idle connections.
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)

# Each instance of SessionLocal is a database session (one per request).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class that all ORM models inherit from.
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
