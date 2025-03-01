import json
from datetime import datetime
import psycopg2
from config import DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT

class ReportManager:
    def __init__(self):
        self.conn = psycopg2.connect(
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
        self._create_table()

    def _create_table(self):
        with self.conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages_logs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP,
                    event TEXT,
                    data JSONB
                );
            """)
            self.conn.commit()

    def log_event(self, event_type, data):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO send_messages_logs (timestamp, event, data) VALUES (%s, %s, %s)",
                (datetime.now(), event_type, json.dumps(data))
            )
            self.conn.commit()