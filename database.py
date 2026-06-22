import aiosqlite

DB = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            user_id INTEGER UNIQUE
        )
        """)
        await db.commit()
