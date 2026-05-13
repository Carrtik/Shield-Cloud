import os
from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "encryption_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['src.workers.tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_concurrency=int(os.environ.get("CELERY_WORKER_CONCURRENCY", 4)),
)
