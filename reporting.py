import json
from datetime import datetime

class ReportManager:
    def __init__(self, filename="reports_{}.json".format(datetime.now().isoformat())):
        self.filename = filename

    def log_event(self, event_type, data):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "data": data
        }
        with open(self.filename, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")