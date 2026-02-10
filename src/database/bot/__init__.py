from database.bot import db

db.run("""
    CREATE TABLE IF NOT EXISTS users (
        discordId TEXT PRIMARY KEY,
        userId TEXT,
        theme JSON,
        commands JSON,
        joined REAL,
        startDate REAL,
        endDate REAL,
        isBanned INTEGER DEFAULT 0,
        isAdmin INTEGER DEFAULT 0,
        isPrivacyWarned INTEGER DEFAULT 0,
        isGgPlus INTEFER DEFAULT 0
    )
""")

db.run("""
    CREATE TABLE IF NOT EXISTS recent_quotes (
        channelId TEXT PRIMARY KEY,
        quoteId TEXT
    )
""")

db.run("""
    CREATE TABLE IF NOT EXISTS chat_usage (
        discordId TEXT PRIMARY KEY,
        usageCount INTEGER DEFAULT 0,
        lastReset REAL
    )
""")

db.run("""
    CREATE TABLE IF NOT EXISTS art (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL UNIQUE,
        image_url TEXT NOT NULL,
        author_id TEXT NOT NULL, -- Discord ID
        timestamp INTEGER NOT NULL
    )
""")