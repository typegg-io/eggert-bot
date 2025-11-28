from database.typegg import db

db.run("""
    CREATE TABLE IF NOT EXISTS users (
        userId TEXT PRIMARY KEY,
        lastAccessed INTEGER NOT NULL -- unix timestamp
    )
""")

db.run("""
    CREATE TABLE IF NOT EXISTS races (
        raceId TEXT PRIMARY KEY,
        quoteId TEXT NOT NULL,
        userId TEXT NOT NULL,
        raceNumber INTEGER,
        pp REAL NOT NULL,
        rawPp REAL NOT NULL,
        wpm REAL NOT NULL,
        rawWpm REAL NOT NULL,
        matchWpm REAL,
        rawMatchWpm REAl,
        duration REAL NOT NULL,
        accuracy REAL NOT NULL,
        errorReactionTime REAL NOT NULL,
        errorRecoveryTime REAL NOT NULL,
        timestamp TEXT NOT NULL, -- ISO 8601 string
        stickyStart INTEGER, -- boolean
        gamemode TEXT NOT NULL,
        placement INTEGER NOT NULL,
        players INTEGER NOT NULL,
        completionType TEXT NOT NULL
    );
""")

db.run("""
    CREATE TABLE IF NOT EXISTS sources (
        sourceId TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        type TEXT NOT NULL,
        thumbnailUrl TEXT NOT NULL,
        publicationYear INTEGER NOT NULL
    );
""")

db.run("""
    CREATE TABLE IF NOT EXISTS quotes (
        quoteId TEXT PRIMARY KEY,
        sourceId TEXT NOT NULL,
        text TEXT NOT NULL,
        explicit INTEGER NOT NULL, -- boolean
        difficulty REAL NOT NULL,
        submittedByUsername TEXT NOT NULL,
        ranked INTEGER NOT NULL, -- boolean
        created TEXT NOT NULL, -- ISO 8601 string
        FOREIGN KEY (sourceId) REFERENCES sources(sourceId)
    );
""")

db.run("""
    CREATE TABLE IF NOT EXISTS daily_quotes (
        dayNumber INTEGER PRIMARY KEY,
        startDate TEXT NOT NULL, -- ISO 8601 string
        endDate TEXT NOT NULL, -- ISO 8601 string
        races INTEGER NOT NULL,
        uniqueUsers INTEGER NOT NULL,
        quoteId TEXT NOT NULL
    )
""")

db.run("""
    CREATE TABLE IF NOT EXISTS daily_quote_results (
        dayNumber INTEGER NOT NULL,
        rank INTEGER NOT NULL,
        raceId TEXT NOT NULL,
        quoteId TEXT NOT NULL,
        userId TEXT NOT NULL,
        username TEXT NOT NULL,
        country TEXT,
        raceNumber INTEGER NOT NULL,
        pp REAL NOT NULL,
        rawPp REAL NOT NULL,
        wpm REAL NOT NULL,
        rawWpm REAL NOT NULL,
        duration REAL NOT NULL,
        accuracy REAL NOT NULL,
        errorReactionTime REAL NOT NULL,
        errorRecoveryTime REAL NOT NULL,
        timestamp TEXT NOT NULL, -- ISO 8601 string
        stickyStart INTEGER NOT NULL, -- boolean
        gamemode TEXT NOT NULL,
        FOREIGN KEY(dayNumber) REFERENCES daily_quotes(dayNumber)
    )
""")

db.run("CREATE INDEX IF NOT EXISTS idx_races_userId on races(userId)")
