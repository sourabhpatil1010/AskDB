from sqlalchemy.ext.asyncio import create_async_engine

# Note: In production, import this from app.core.config
SQLALCHEMY_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/askdb"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
    future=True,
    pool_size=5,
    max_overflow=10
)
