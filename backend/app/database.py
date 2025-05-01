from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()



engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True,
    pool_pre_ping=True,
    # Optimize pool settings
    pool_size=10,  # Default is usually 5
    max_overflow=20,
    pool_timeout=30,  # Default is often too long (30-60 seconds)
    pool_recycle=1800,  # Recycle connections after 30 minutes
    # Optimize connection parameters for aiomysql
    connect_args={
        "connect_timeout": 10,  # aiomysql uses connect_timeout instead of timeout
        "charset": "utf8mb4",
        "use_unicode": True,
        # Remove autocommit as it's handled by SQLAlchemy
    }
)


AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


# Database dependency for FastAPI
async def get_db():
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()
