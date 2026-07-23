"""独立 Worker 进程：消费 Redis Stream 队列，调用 IngestionService 处理文档。"""
from __future__ import annotations

import logging
import os
import signal
import socket
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from core.config import config
from core.task_queue import TaskQueue, TaskMessage
from core.services import create_infra
from core.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)

GROUP = "ingestion-workers"

_shutdown = threading.Event()


def _signal_handler(signum, frame):
    logger.info("Received signal %d, shutting down...", signum)
    _shutdown.set()


def process_message(
    queue: TaskQueue,
    ingestion: IngestionService,
    item: dict,
    max_retries: int = 3,
):
    """Process a single message (called by thread pool)

    Args:
        queue: TaskQueue instance
        ingestion: Document ingestion service
        item: dict from dequeue with keys: stream, id, msg
        max_retries: Max retry count
    """
    msg: TaskMessage = item["msg"]
    stream: str = item["stream"]
    msg_id: str = item["id"]
    task_id = msg.task_id

    try:
        # Phase: parsing
        queue.update_state(task_id, status="processing", phase="parsing")

        # Phase: chunking
        queue.update_state(task_id, phase="chunking")

        # Phase: embedding
        queue.update_state(task_id, phase="embedding")

        # Phase: indexing
        queue.update_state(task_id, phase="indexing")

        chunks = ingestion.ingest_document(msg.file_path)

        # Complete
        queue.update_state(
            task_id,
            status="completed",
            phase="done",
            chunks=str(chunks),
            completed_at=str(time.time()),
        )
        queue.ack(stream, msg_id)
        logger.info("Task %s completed: %d chunks", task_id, chunks)

    except Exception as e:
        logger.error("Task %s failed: %s", task_id, e, exc_info=True)

        if msg.retry < max_retries:
            queue.ack(stream, msg_id)
            queue.requeue(msg)
        else:
            queue.update_state(
                task_id,
                status="failed",
                error=str(e),
                completed_at=str(time.time()),
            )
            queue.ack(stream, msg_id)
            logger.error("Task %s permanently failed after %d retries", task_id, msg.retry)


def main():
    """Worker main entry"""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    consumer_name = f"worker-{socket.gethostname()}-{os.getpid()}"
    logger.info("Starting worker: %s", consumer_name)

    queue = TaskQueue(config.REDIS_URL, task_ttl=config.TASK_TTL_HOURS * 3600)
    queue.ensure_consumer_group(GROUP)

    infra = create_infra(config)
    ingestion = IngestionService(infra)

    max_retries = config.WORKER_MAX_RETRIES
    concurrency = config.WORKER_CONCURRENCY
    logger.info("Worker ready: concurrency=%d, max_retries=%d", concurrency, max_retries)

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        while not _shutdown.is_set():
            try:
                messages = queue.dequeue(GROUP, consumer_name, count=1)
                for item in messages:
                    if _shutdown.is_set():
                        break
                    pool.submit(process_message, queue, ingestion, item, max_retries)
            except Exception as e:
                logger.error("Worker loop error: %s", e, exc_info=True)
                if not _shutdown.is_set():
                    _shutdown.wait(timeout=5)

    logger.info("Worker shut down gracefully")

    try:
        ingestion.close()
    except Exception:
        pass
    if infra.executor:
        infra.executor.shutdown(wait=False)


if __name__ == "__main__":
    main()
