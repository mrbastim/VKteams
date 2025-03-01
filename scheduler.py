import time
from datetime import datetime
from commands import reporter


scheduled_jobs = []

def add_job(bot, scheduled_time, chat_id, text):
    scheduled_jobs.append({
        "bot": bot,
        "time": scheduled_time,
        "chat_id": chat_id,
        "text": text
    })
def remove_all_jobs():
    scheduled_jobs.clear()


def start_scheduler():
    while True:
        now = datetime.now()
        for job in scheduled_jobs[:]:
            if now >= job["time"]:
                job["bot"].send_text(chat_id=job["chat_id"], text=job["text"])
                reporter.log_event("scheduled_message", {"chat_id": job["chat_id"], "text": job["text"]})
                scheduled_jobs.remove(job)
        time.sleep(1)