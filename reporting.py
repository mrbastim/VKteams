import json
from datetime import datetime, timedelta
import os
# import psycopg2
# from config import DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT

class ReportManager:
# def __init__(self):
    #     self.conn = psycopg2.connect(
    #         database=DB_NAME,
    #         user=DB_USER,
    #         password=DB_PASS,
    #         host=DB_HOST,
    #         port=DB_PORT
    #     )
    #     self._create_table()

    # def _create_table(self):
    #     with self.conn.cursor() as cursor:
    #         cursor.execute("""
    #             CREATE TABLE IF NOT EXISTS messages_logs (
    #                 id SERIAL PRIMARY KEY,
    #                 timestamp TIMESTAMP,
    #                 event TEXT,
    #                 data JSONB
    #             );
    #         """)
    #         self.conn.commit()

    # def log_event(self, event_type, data):
    #     with self.conn.cursor() as cursor:
    #         cursor.execute(
    #             "INSERT INTO messages_logs (timestamp, event, data) VALUES (%s, %s, %s)",
    #             (datetime.now(), event_type, json.dumps(data))
    #         )
    #         self.conn.commit()

    def __init__(self, logs_dir="logs", buffer_limit=10):
        self.logs_dir = logs_dir
        self.buffer_limit = buffer_limit
        self.buffer = []  # буфер для накопления логов

        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
        self._clean_old_logs()
        self.filename = os.path.join(
            self.logs_dir,
            "logs-{}.json".format(datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        )

    def _clean_old_logs(self):
        cutoff = datetime.now() - timedelta(days=30)
        for file in os.listdir(self.logs_dir):
            filepath = os.path.join(self.logs_dir, file)
            if os.path.isfile(filepath):
                file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                if file_mtime < cutoff:
                    os.remove(filepath)

    def log_event(self, event_type, data):
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
            "event": event_type,
            "data": data
        }
        self.buffer.append(entry)
        if len(self.buffer) >= self.buffer_limit:
            self.flush()

    def flush(self):
        if self.buffer:
            logs = []
            if os.path.exists(self.filename):
                try:
                    with open(self.filename, "r", encoding="utf-8") as f:
                        logs = json.load(f)
                except json.JSONDecodeError:
                    logs = []
            logs.extend(self.buffer)
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            self.buffer = []

    def __del__(self):
        self.flush()
