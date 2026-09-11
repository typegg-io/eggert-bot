"""users.db schema. Importing this module creates any missing tables."""

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
        isGgPlus INTEFER DEFAULT 0,
        timezone DEFAULT "UTC",
        universe DEFAULT "en",
        leaderboardPage DEFAULT "me" -- 'me' or 'top'
    )
""")

# users shipped without universe, so a database made before the split catches up here.
if not db.fetch("SELECT 1 FROM pragma_table_info('users') WHERE name = 'universe'"):
    db.run('ALTER TABLE users ADD COLUMN universe DEFAULT "en"')

# users shipped without leaderboardPage, so an older database catches up here.
if not db.fetch("SELECT 1 FROM pragma_table_info('users') WHERE name = 'leaderboardPage'"):
    db.run('ALTER TABLE users ADD COLUMN leaderboardPage DEFAULT "me"')

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

db.run("""
    CREATE TABLE IF NOT EXISTS command_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        discordId TEXT NOT NULL,
        userId TEXT, -- the linked TypeGG ID at time of use, never joined
        command TEXT NOT NULL, -- canonical name, never an alias
        origin TEXT NOT NULL, -- 'server' or 'dm'
        serverId TEXT, -- NULL on DMs, and on backfilled rows the log could not place
        timestamp REAL -- NULL on backfilled rows the log could not date
    )
""")

# command_log shipped without serverId, so a database made in that window catches up here.
if not db.fetch("SELECT 1 FROM pragma_table_info('command_log') WHERE name = 'serverId'"):
    db.run("ALTER TABLE command_log ADD COLUMN serverId TEXT")

db.run("CREATE INDEX IF NOT EXISTS idx_command_log_discordId ON command_log (discordId)")
db.run("CREATE INDEX IF NOT EXISTS idx_command_log_command ON command_log (command)")
db.run("CREATE INDEX IF NOT EXISTS idx_command_log_discordId_command ON command_log (discordId, command)")
db.run("CREATE INDEX IF NOT EXISTS idx_command_log_timestamp ON command_log (timestamp)")
db.run("CREATE INDEX IF NOT EXISTS idx_command_log_serverId ON command_log (serverId)")

# Discord serves no name for a guild the bot has left, so names are kept as they are seen.
db.run("""
    CREATE TABLE IF NOT EXISTS servers (
        serverId TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        lastSeen REAL NOT NULL
    )
""")
