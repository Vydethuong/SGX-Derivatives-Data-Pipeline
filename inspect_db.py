import sqlite3

conn = sqlite3.connect("logs/db_log.db")
cur = conn.cursor()

rows = cur.execute(
    "SELECT id, log_time, level, message, context "
    "FROM error_logs ORDER BY log_time DESC LIMIT 20"
).fetchall()

for r in rows:
    print(r)

conn.close()
