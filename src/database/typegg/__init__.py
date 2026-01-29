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
        quoteId TEXT NOT NULL REFERENCES quotes(quoteId) ON UPDATE CASCADE ON DELETE CASCADE,
        userId TEXT NOT NULL,
        matchId TEXT,
        raceNumber INTEGER,
        pp REAL NOT NULL,
        rawPp REAL NOT NULL,
        wpm REAL NOT NULL,
        rawWpm REAL NOT NULL,
        duration REAL NOT NULL,
        accuracy REAL NOT NULL,
        errorReactionTime REAL NOT NULL,
        errorRecoveryTime REAL NOT NULL,
        timestamp TEXT NOT NULL, -- ISO 8601 string
        stickyStart INTEGER -- boolean
    );
""")

db.run("CREATE INDEX IF NOT EXISTS idx_races_userId on races(userId)")
db.run("CREATE INDEX IF NOT EXISTS idx_races_userId_quoteId on races(userId, quoteId)")

db.run("""
    CREATE TABLE IF NOT EXISTS keystroke_data (
        raceId TEXT PRIMARY KEY REFERENCES races(raceId) ON DELETE CASCADE,
        keystrokeData BLOB NOT NULL,
        compressed INTEGER NOT NULL DEFAULT 0 -- boolean
    )
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
        sourceId TEXT NOT NULL REFERENCES sources(sourceId) ON UPDATE CASCADE ON DELETE CASCADE,
        text TEXT NOT NULL,
        explicit INTEGER NOT NULL, -- boolean
        difficulty REAL NOT NULL,
        complexity REAL NOT NULL,
        submittedByUsername TEXT NOT NULL,
        ranked INTEGER NOT NULL, -- boolean
        created TEXT NOT NULL, -- ISO 8601 string
        language TEXT NOT NULL,
        formatting TEXT -- JSON
    );
""")

db.run("""
    CREATE TABLE IF NOT EXISTS daily_quotes (
        dayNumber INTEGER PRIMARY KEY,
        quoteId TEXT NOT NULL REFERENCES quotes(quoteId) ON UPDATE CASCADE ON DELETE CASCADE,
        startDate TEXT NOT NULL, -- ISO 8601 string
        endDate TEXT NOT NULL, -- ISO 8601 string
        races INTEGER NOT NULL,
        uniqueUsers INTEGER NOT NULL
    )
""")

db.run("""
    CREATE TABLE IF NOT EXISTS daily_quote_results (
        dayNumber INTEGER NOT NULL REFERENCES daily_quotes(dayNumber) ON DELETE CASCADE,
        rank INTEGER NOT NULL,
        raceId TEXT NOT NULL,
        quoteId TEXT NOT NULL REFERENCES quotes(quoteId) ON UPDATE CASCADE ON DELETE CASCADE,
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
        gamemode TEXT NOT NULL
    )
""")

db.run("""
    CREATE TABLE IF NOT EXISTS daily_quote_id (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        quoteId TEXT NOT NULL REFERENCES quotes(quoteId) ON UPDATE CASCADE ON DELETE CASCADE
    )
""")

db.run("""
    CREATE TABLE IF NOT EXISTS matches (
        matchId TEXT PRIMARY KEY,
        quoteId TEXT NOT NULL REFERENCES quotes(quoteId) ON UPDATE CASCADE ON DELETE CASCADE,
        startTimestamp TEXT NOT NULL, -- ISO 8601 string
        gamemode TEXT NOT NULL,
        players INTEGER NOT NULL
    )
""")

db.run("""
    CREATE TABLE IF NOT EXISTS match_results (
        matchId TEXT NOT NULL,
        userId TEXT,
        botId TEXT,
        username TEXT,
        raceNumber INTEGER,
        matchWpm REAL,
        rawMatchWpm REAL,
        matchPp REAL,
        rawMatchPp REAL,
        startTime INTEGER,
        accuracy REAL,
        placement INTEGER,
        completionType TEXT,
        timestamp TEXT -- ISO 8601 string
    )
""")

db.run("""CREATE UNIQUE INDEX IF NOT EXISTS idx_match_results_matchId_userId ON match_results(matchId, userId)""")
db.run("CREATE INDEX IF NOT EXISTS idx_races_matchId_userId ON races(matchId, userId)")

db.run("""
    CREATE VIEW IF NOT EXISTS multiplayer_races AS
    SELECT
        mr.matchId,
        mr.userId,
        m.quoteId,
        mr.raceNumber,
        r.raceId,
        r.duration,
        r.accuracy,
        r.errorReactionTime,
        r.errorRecoveryTime,
        r.stickyStart,
        mr.matchWpm as wpm,
        mr.rawMatchWpm as rawWpm,
        mr.matchPp as pp,
        mr.rawMatchPp as rawPp,
        mr.completionType,
        mr.timestamp,
        mr.placement,
        m.gamemode,
        m.players
    FROM match_results mr
    LEFT JOIN races r ON r.matchId = mr.matchId AND r.userId = mr.userId
    JOIN matches m ON m.matchId = mr.matchId
""")

db.run("""
    CREATE VIEW IF NOT EXISTS encounters AS
    SELECT
        mr.matchId,
        mr.userId AS userId,
        mr.placement AS userPlacement,
        mr.matchWpm as userWpm,
        mr.rawMatchWpm as userRawWpm,
        mr.accuracy as userAccuracy,
        mr.completionType != 'finished' AS userDnf,
        mr.startTime AS userStartTime,
        opp.userId AS opponentId,
        opp.username AS opponentUsername,
        opp.placement AS opponentPlacement,
        opp.matchWpm as opponentWpm,
        opp.rawMatchWpm as opponentRawWpm,
        opp.accuracy as opponentAccuracy,
        opp.completionType != 'finished' AS opponentDnf,
        opp.startTime as opponentStartTime,
        opp.botId IS NOT '' AS isBot,
        mr.timestamp AS timestamp,
        m.gamemode,
        m.quoteId
    FROM match_results mr
    JOIN match_results opp
    ON opp.matchId = mr.matchId
    AND opp.userId != mr.userId
    JOIN matches m
    ON m.matchId = mr.matchId
""")
