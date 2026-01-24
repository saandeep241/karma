"""Database connection and session management for Karma.
Supports both SQLite (local development) and PostgreSQL (Cloud SQL).
"""

from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import event, text
from .models import Base
from app.config import get_settings

settings = get_settings()

# Determine which database to use
use_postgresql = settings.use_postgresql

if use_postgresql:
    # PostgreSQL (Cloud SQL)
    if settings.database_url:
        # Use provided full database URL
        DATABASE_URL = settings.database_url
    elif settings.cloud_sql_connection_name:
        # Use Unix socket connection (recommended for Cloud Run)
        # Format: postgresql+asyncpg://USER:PASSWORD@/DATABASE?host=/cloudsql/CONNECTION_NAME
        user = settings.database_user
        password = settings.database_password or ""
        database = settings.database_name
        connection_name = settings.cloud_sql_connection_name
        
        DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@/{database}?host=/cloudsql/{connection_name}"
    elif settings.database_host:
        # Use TCP connection
        user = settings.database_user
        password = settings.database_password or ""
        host = settings.database_host
        port = settings.database_port
        database = settings.database_name
        
        DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
    else:
        # Fallback to SQLite if PostgreSQL config is incomplete
        print("⚠️ PostgreSQL config incomplete, falling back to SQLite")
        use_postgresql = False

if not use_postgresql:
    # SQLite (local development)
    DATA_DIR = Path(__file__).parent.parent.parent / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_PATH = DATA_DIR / "karma.db"
    DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"

# Create async engine with appropriate settings
if use_postgresql:
    # PostgreSQL engine settings
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # Set to True for SQL debugging
        future=True,
        pool_size=5,  # Connection pool size
        max_overflow=10,  # Max overflow connections
        pool_pre_ping=True,  # Verify connections before using
    )
    print(f"📦 Using PostgreSQL database: {settings.database_name}")
else:
    # SQLite engine settings
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
    
    print(f"📦 Using SQLite database: {DATABASE_PATH}")

# Create async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize the database, creating all tables."""
    async with engine.begin() as conn:
        if use_postgresql:
            # PostgreSQL doesn't need PRAGMA, but we can check connection
            await conn.execute(text("SELECT 1"))
        else:
            # Enable foreign keys for SQLite
            await conn.run_sync(lambda sync_conn: sync_conn.execute(
                text("PRAGMA foreign_keys=ON")
            ))
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    if use_postgresql:
        print(f"📦 PostgreSQL database initialized: {settings.database_name}")
    else:
        print(f"📦 SQLite database initialized at {DATABASE_PATH}")


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
    
    if use_postgresql:
        # PostgreSQL sync connection
        if settings.database_url:
            sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
        elif settings.database_host:
            user = settings.database_user
            password = settings.database_password or ""
            host = settings.database_host
            port = settings.database_port
            database = settings.database_name
            sync_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
        else:
            # Can't use Unix socket with sync driver easily, fallback to async
            raise RuntimeError("Synchronous PostgreSQL connection requires database_host or database_url")
        
        sync_engine = create_engine(sync_url, echo=False)
    else:
        # SQLite sync connection
        sync_engine = create_engine(
            f"sqlite:///{DATABASE_PATH}",
            echo=False,
        )
    
    Session = sessionmaker(bind=sync_engine)
    return Session()
