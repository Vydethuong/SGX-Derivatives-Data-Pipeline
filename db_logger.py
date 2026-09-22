import logging
import sqlite3
import os
import json

class DBLogHandler(logging.Handler):
    def __init__(self, db_path="logs/db_log.db", batch_size=20):
        super().__init__(level=logging.ERROR)  # save only ERROR+
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_table()
        self.buffer = []
        self.batch_size = batch_size

    def _init_table(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT,
                message TEXT,
                context TEXT
            )
        """)
        self.conn.commit()

    def emit(self, record):
        try:
            msg = self.format(record)
            ctx = {
                "module": record.module,
                "func": record.funcName,
                "line": record.lineno
            }
            self.buffer.append((record.levelname, msg, json.dumps(ctx)))
            if len(self.buffer) >= self.batch_size:
                self.flush()
        except Exception as e:
            print("DBLogHandler emit error:", e)

    def flush(self):
        if not self.buffer:
            return
        try:
            cur = self.conn.cursor()
            cur.executemany(
                "INSERT INTO error_logs (level, message, context) VALUES (?, ?, ?)",
                self.buffer
            )
            self.conn.commit()
            self.buffer = []
        except Exception as e:
            print("DBLogHandler flush error:", e)

    def close(self):
        try:
            self.flush()
            self.conn.close()
        except Exception:
            pass
        super().close()
