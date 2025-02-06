import json

import config
from database import db

db.run("UPDATE users SET user_id = ? WHERE discord_id = ?", ["keegan", 155481579005804544])
# db.run("DELETE FROM users")