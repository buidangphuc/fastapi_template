import ssl
import sys
import time
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.sql import text

from common.log import log
from common.model import Base
from core.conf import settings

# Use PostgreSQL database URL
db_url = settings.POSTGRES_URL

# Initialize the asynchronous database engine and session factory
engine = create_async_engine(db_url, echo=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


async def init_db():
    """Initialize the database by creating all tables."""
    log.info("Starting database initialization...")

    try:
        async with engine.begin() as conn:
            # Create all tables from the Base class
            await conn.run_sync(Base.metadata.create_all)
            log.info("✅ Database initialization successful: All tables created.")

    except Exception as e:
        log.error(f"❌ Failed to initialize database: {e}")
        raise


async def get_db():
    """Provide a database session with explicit transaction management."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_connection(
    max_retries: int = 3, retry_interval: int = 1, for_health_check: bool = False
) -> tuple[bool, str] | None:
    """Check connection to Database with retries if necessary."""
    for attempt in range(max_retries):
        try:
            # Add actual connection test
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))

            log.success("✅ Database connection to PostgreSQL successful")

            if for_health_check:
                return True, "Database connection successful"
            return
        except Exception as e:
            remaining_retries = max_retries - attempt - 1
            if remaining_retries == 0:
                log.error(f"❌ Failed to connect to Database: {e}")

                if for_health_check:
                    return False, str(e)
                sys.exit(1)
            else:
                log.warning(
                    f"Retrying Database connection... {remaining_retries} retries left"
                )
                time.sleep(retry_interval)


CurrentSession = Annotated[AsyncSessionLocal, Depends(get_db)]
