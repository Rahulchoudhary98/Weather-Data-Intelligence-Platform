
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app import settings


# Build the database connection URL safely.
# URL.create handles special characters in passwords.
DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=settings.DB_USER,
    password=settings.DB_PASSWORD,
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    database=settings.DB_NAME,
    query={"charset": "utf8mb4"},
)


# Create the SQLAlchemy database engine.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)


# Create a reusable database session factory.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


# Base class for all database models.
class Base(DeclarativeBase):
    pass


# Provide a database session to API endpoints.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
