import logging
import asyncio
import sys
from datetime import datetime, timezone
import json
import traceback

from data.mongo_log_repository import MongoLogRepository

class AsyncMongoLogHandler(logging.Handler):
    """
    A custom logging handler that sends log records to MongoDB asynchronously.
    It queues logs and sends them to MongoDB via a background asyncio task.
    """
    def __init__(self, connection_uri: str, database_name: str = "RoundZero"):
        super().__init__()
        self.repo = MongoLogRepository(connection_uri, database_name)
        self.queue = asyncio.Queue()
        self.batch_size = 50
        self.flush_interval = 2.0 # seconds
        self._worker_task = None
        self._is_running = False

    def emit(self, record):
        """Standard logging handler emit method. Queues the record."""
        try:
            # We need to extract the information we want while we are synchronous
            msg = self.format(record)
            
            # Create a dict representation of the log record
            log_doc = {
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "name": record.name,
                "level": record.levelname,
                "message": msg,
                "module": record.module,
                "funcName": record.funcName,
                "lineno": record.lineno,
            }

            # Add extra fields if they exist (e.g., from structlog or passed manually)
            if hasattr(record, "extra") and isinstance(record.extra, dict):
                 log_doc["extra"] = record.extra
            
            # Capture exception tracebacks if present
            if record.exc_info:
                 log_doc["exception"] = "".join(traceback.format_exception(*record.exc_info))

            # Put object into the queue non-blockingly
            try:
                self.queue.put_nowait(log_doc)
            except asyncio.QueueFull:
                print(f"[AsyncMongoLogHandler Error] Log queue is full. Dropping log: {msg}", file=sys.stderr)
        except Exception as e:
            self.handleError(record)

    async def _worker(self):
        """Background task to flush logs to MongoDB in batches."""
        self._is_running = True
        await self.repo.create_indexes()
        
        while self._is_running:
            batch = []
            try:
                # Wait for the first log in the batch
                try:
                    first_log = await asyncio.wait_for(self.queue.get(), timeout=self.flush_interval)
                    batch.append(first_log)
                    self.queue.task_done()
                except asyncio.TimeoutError:
                    # No logs in this interval, loop again
                    pass

                # Drain the queue up to batch_size
                if batch:
                    while len(batch) < self.batch_size:
                        try:
                            log = self.queue.get_nowait()
                            batch.append(log)
                            self.queue.task_done()
                        except asyncio.QueueEmpty:
                            break

                    filtered = [b for b in batch if "_stop_signal" not in b]
                    if filtered:
                        await self.repo.insert_logs_batch(filtered)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[AsyncMongoLogHandler Error] Worker exception: {e}", file=sys.stderr)
                await asyncio.sleep(5)  # Backoff on error

        # Final flush on shutdown
        await self._flush_remaining()

    async def _flush_remaining(self):
        """Flushes any remaining items in the queue."""
        batch = []
        while not self.queue.empty():
            try:
                log = self.queue.get_nowait()
                batch.append(log)
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break
        
        if batch:
            filtered = [b for b in batch if "_stop_signal" not in b]
            if filtered:
                try:
                    await self.repo.insert_logs_batch(filtered)
                except Exception as e:
                    print(f"[AsyncMongoLogHandler Error] Final flush exception: {e}", file=sys.stderr)
        
        await self.repo.close()

    def start_worker(self):
        """Starts the background worker task. Must be called in the running event loop."""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker())

    async def stop_worker(self):
        """Stops the worker task gracefully without cancelling so it can flush."""
        self._is_running = False
        if self._worker_task:
            # We can put a dummy item to wake up the queue if it's waiting
            try:
                self.queue.put_nowait({"_stop_signal": True})
            except asyncio.QueueFull:
                pass
            
            try:
                # Give it up to 5 seconds to flush normally
                await asyncio.wait_for(self._worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                # Force cancel if it stuck
                self._worker_task.cancel()
                try:
                    await self._worker_task
                except asyncio.CancelledError:
                    pass

_mongo_handler_instance = None

def setup_mongo_logging(connection_uri: str, database_name: str = "RoundZero"):
    """
    Configures the root logger to use the AsyncMongoLogHandler.
    Returns the handler instance so `start_worker()` and `stop_worker()` can be called.
    """
    global _mongo_handler_instance
    
    if _mongo_handler_instance is not None:
         return _mongo_handler_instance
         
    # Create the custom handler
    handler = AsyncMongoLogHandler(connection_uri, database_name)
    formatter = logging.Formatter('%(message)s') # Just the message, MongoDB gets the structured fields
    handler.setFormatter(formatter)
    
    # We only want to log INFO and above in the DB by default
    handler.setLevel(logging.INFO)
    
    # Attach to root logger
    root_logger = logging.getLogger()
    # Or to specific app loggers: 
    # app_logger = logging.getLogger("roundzero")
    # app_logger.addHandler(handler)
    
    root_logger.addHandler(handler)
    _mongo_handler_instance = handler
    
    return handler
