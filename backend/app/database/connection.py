"""Database connection and session management for Karma."""

import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import event
from .models import Base
from app.config import get_settings

# Get settings
settings = get_settings()

# Determine which database to use
if settings.use_postgresql:
    # PostgreSQL/Cloud SQL configuration
    connection_name = settings.cloud_sql_connection_name
    db_user = settings.database_user
    db_password = settings.database_password
    db_name = settings.database_name
    
    if not db_password:
        raise ValueError("DATABASE_PASSWORD is required for PostgreSQL but not set")
    
    # Use Unix socket for Cloud SQL (recommended for Cloud Run)
    # Format: postgresql+asyncpg://USER:PASSWORD@/DATABASE?host=/cloudsql/CONNECTION_NAME
    # URL encode password to handle special characters
    from urllib.parse import quote_plus
    encoded_password = quote_plus(db_password)
    
    if connection_name:
        DATABASE_URL = f"postgresql+asyncpg://{db_user}:{encoded_password}@/{db_name}?host=/cloudsql/{connection_name}"
        print(f"🔗 Using PostgreSQL via Cloud SQL Unix socket: {connection_name}")
    elif settings.database_host:
        # Fallback to TCP connection if host is provided
        db_host = settings.database_host
        db_port = settings.database_port
        DATABASE_URL = f"postgresql+asyncpg://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
        print(f"🔗 Using PostgreSQL via TCP: {db_host}:{db_port}")
    else:
        raise ValueError("Either CLOUD_SQL_CONNECTION_NAME or DATABASE_HOST must be set for PostgreSQL")
    
    DATABASE_TYPE = "PostgreSQL"
    DATABASE_PATH = None
else:
    # SQLite configuration (local development)
    DATA_DIR = Path(__file__).parent.parent.parent / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_PATH = DATA_DIR / "karma.db"
    DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"
    DATABASE_TYPE = "SQLite"
    print(f"🔗 Using SQLite database at: {DATABASE_PATH}")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    future=True,
)

# Enable foreign keys for SQLite on every connection (only for SQLite)
if not settings.use_postgresql:
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
        if not settings.use_postgresql:
            # Enable foreign keys for SQLite
            await conn.run_sync(lambda sync_conn: sync_conn.execute(
                __import__('sqlalchemy').text("PRAGMA foreign_keys=ON")
            ))
        # Create all tables (works for both SQLite and PostgreSQL)
        await conn.run_sync(Base.metadata.create_all)
    
    if DATABASE_PATH:
        print(f"📦 Database initialized: {DATABASE_TYPE} at {DATABASE_PATH}")
    else:
        print(f"📦 Database initialized: {DATABASE_TYPE} (Cloud SQL: {settings.cloud_sql_connection_name})")


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
    
    if settings.use_postgresql:
        # PostgreSQL synchronous connection
        connection_name = settings.cloud_sql_connection_name
        db_user = settings.database_user
        db_password = settings.database_password
        db_name = settings.database_name
        
        from urllib.parse import quote_plus
        encoded_password = quote_plus(db_password)
        
        if connection_name:
            sync_url = f"postgresql://{db_user}:{encoded_password}@/{db_name}?host=/cloudsql/{connection_name}"
        elif settings.database_host:
            sync_url = f"postgresql://{db_user}:{encoded_password}@{settings.database_host}:{settings.database_port}/{db_name}"
        else:
            raise ValueError("PostgreSQL configuration incomplete")
        
        sync_engine = create_engine(sync_url, echo=False)
    else:
        # SQLite synchronous connection
        sync_engine = create_engine(
            f"sqlite:///{DATABASE_PATH}",
            echo=False,
        )
    
    Session = sessionmaker(bind=sync_engine)
    return Session()

