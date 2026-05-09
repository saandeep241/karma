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
    DATABASE_TYPE = "PostgreSQL"
    DATABASE_PATH = None

    if settings.database_url:
        # Replit (and other providers) supply a standard postgresql:// URL.
        # asyncpg requires the postgresql+asyncpg:// scheme.
        # asyncpg also does not accept sslmode= in the URL — strip it and
        # pass ssl via connect_args instead.
        from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
        raw_url = settings.database_url
        if raw_url.startswith("postgres://"):
            raw_url = raw_url.replace("postgres://", "postgresql://", 1)

        parsed = urlparse(raw_url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        sslmode = qs.pop("sslmode", ["disable"])[0]  # remove from URL; default disable
        clean_query = urlencode({k: v[0] for k, v in qs.items()})
        clean_parsed = parsed._replace(query=clean_query, scheme="postgresql+asyncpg")
        DATABASE_URL = urlunparse(clean_parsed)

        # Translate sslmode to asyncpg ssl argument
        _SSL_REQUIRE = sslmode in ("require", "verify-ca", "verify-full")
        print(f"🔗 Using PostgreSQL via DATABASE_URL (ssl={'on' if _SSL_REQUIRE else 'off'})")

    else:
        # Cloud SQL / explicit credentials configuration
        from urllib.parse import quote_plus
        connection_name = settings.cloud_sql_connection_name
        db_user = settings.database_user
        db_password = settings.database_password
        db_name = settings.database_name

        if not db_password:
            raise ValueError("DATABASE_PASSWORD is required for PostgreSQL but not set")

        encoded_password = quote_plus(db_password)

        if connection_name:
            DATABASE_URL = f"postgresql+asyncpg://{db_user}:{encoded_password}@/{db_name}?host=/cloudsql/{connection_name}"
            print(f"🔗 Using PostgreSQL via Cloud SQL Unix socket: {connection_name}")
        elif settings.database_host:
            db_host = settings.database_host
            db_port = settings.database_port
            DATABASE_URL = f"postgresql+asyncpg://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
            print(f"🔗 Using PostgreSQL via TCP: {db_host}:{db_port}")
        else:
            raise ValueError("Either CLOUD_SQL_CONNECTION_NAME or DATABASE_HOST must be set for PostgreSQL")
else:
    # SQLite configuration (local development)
    DATA_DIR = Path(__file__).parent.parent.parent / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_PATH = DATA_DIR / "karma.db"
    DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"
    DATABASE_TYPE = "SQLite"
    print(f"🔗 Using SQLite database at: {DATABASE_PATH}")

# Create async engine
engine_kwargs = {
    "echo": False,  # Set to True for SQL debugging
    "future": True,
}

if not settings.use_postgresql:
    # Increase SQLite lock wait timeout to reduce "database is locked" under write bursts.
    engine_kwargs["connect_args"] = {"timeout": 30}
elif settings.database_url and _SSL_REQUIRE:
    # asyncpg requires ssl to be passed as a connect_arg, not in the URL
    engine_kwargs["connect_args"] = {"ssl": "require"}

engine = create_async_engine(
    DATABASE_URL,
    **engine_kwargs,
)

# Enable foreign keys for SQLite on every connection (only for SQLite)
if not settings.use_postgresql:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Enable foreign keys for SQLite on each connection."""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA journal_mode=WAL")
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
    elif settings.database_url:
        print(f"📦 Database initialized: {DATABASE_TYPE} (via DATABASE_URL)")
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
        if settings.database_url:
            raw_url = settings.database_url
            if raw_url.startswith("postgresql+asyncpg://"):
                sync_url = raw_url.replace("postgresql+asyncpg://", "postgresql://", 1)
            elif raw_url.startswith("postgres://"):
                sync_url = raw_url.replace("postgres://", "postgresql://", 1)
            else:
                sync_url = raw_url
        else:
            from urllib.parse import quote_plus
            connection_name = settings.cloud_sql_connection_name
            db_user = settings.database_user
            db_password = settings.database_password
            db_name = settings.database_name
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
