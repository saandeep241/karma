"""Database connection and session management for Karma."""

from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import event
from .models import Base

# Database file location
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = DATA_DIR / "karma.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    future=True,
)

# Enable foreign keys for SQLite on every connection
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign keys for SQLite on each connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Create async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize the database, creating all tables."""
    async with engine.begin() as conn:
        # Enable foreign keys for SQLite
        await conn.run_sync(lambda sync_conn: sync_conn.execute(
            __import__('sqlalchemy').text("PRAGMA foreign_keys=ON")
        ))
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    print(f"📦 Database initialized at {DATABASE_PATH}")


async def get_db() -> AsyncSession:
    """Get a database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


# Synchronous helper for non-async contexts
def get_sync_session():
    """Get a synchronous session for non-async contexts."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    sync_engine = create_engine(
        f"sqlite:///{DATABASE_PATH}",
        echo=False,
    )
    Session = sessionmaker(bind=sync_engine)
    return Session()

