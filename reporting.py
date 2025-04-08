import json
from datetime import datetime, timedelta
import os

class ReportManager:

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
