import aiosqlite
import os
from config import DB_PATH

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


async def get_connection() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("PRAGMA foreign_keys=ON;")
    return conn


async def init_db() -> None:
    with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()

    conn = await get_connection()
    try:
        await conn.executescript(schema)
        await conn.commit()
    finally:
        await conn.close()
