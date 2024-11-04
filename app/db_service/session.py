from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import DATABASE_URL


async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)
session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
