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
        isPrivacyWarned INTEGER DEFAULT 0
    )
""")