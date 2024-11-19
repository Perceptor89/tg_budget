import enum
from logging import getLogger
from typing import Callable, Optional

from redis import Redis
from rq import Queue, job

from app.core import config


KEEP_RESULTS_FOR = config.ONE_HOUR

logger = getLogger('rq')


class QueueName(str, enum.Enum):
    """Redis queues names."""

    SEND = 'send'


class QueueManager:
    """Redis queue manager class."""

    host: str
    port: int
    username: Optional[str]
    password: Optional[str]
    db_number: int
    is_running: bool = False
    connection: Optional[Redis] = None
    queues: Optional[dict[str, Queue]] = None

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db_number: int = 0,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """Create new queue manager object."""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.db_number = db_number
        self.queues = dict()

    def start(self):
        try:
            self.connection = Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                username=self.username,
                db=self.db_number,
            )
            self.is_running = True
        except Exception as error:
            logger.exception('RQ_START-E %s', error)

        logger.info('RQ_START running %s', self.is_running)

    def get_queue(self, name='default'):
        if name not in self.queues:
            self.queues[name] = Queue(name, connection=self.connection)
        return self.queues[name]

    def stop(self):
        self.is_running = False
        if self.connection:
            self.connection.close()

    # def lock_and_enqueue(
    #     self,
    #     func: Callable,
    #     queue_name: str,
    #     *,
    #     job_id: Optional[str] = None,
    #     ex: int = 60,
    #     job_timeout: int = config.ONE_HOUR,
    #     **kwargs,
    # ):
    #     if not self.is_running:
    #         logger.error('RQ-E job[%s] manager inactive', job_id)
    #         return

    #     if self.connection.set(f'task_lock:{job_id}', 'lock', nx=True, ex=ex):
    #         try:
    #             queue = self.get_queue(name=queue_name)
    #             queue.enqueue(
    #                 func, job_id=job_id, result_ttl=KEEP_RESULTS_FOR, job_timeout=job_timeout,
    #                 **kwargs,
    #             )
    #             logger.debug('RG queued %s', job_id)
    #         except Exception as error:
    #             logger.error('RQ-E job[%s] %s', job_id, error)

    def enqueue(
        self,
        func: Callable,
        queue_name: str,
        *,
        job_timeout: int = config.ONE_MINUTE * 1,
        **kwargs,
    ) -> job.Job:
        try:
            queue = self.get_queue(name=queue_name)
            job = queue.enqueue(
                func, result_ttl=KEEP_RESULTS_FOR, job_timeout=job_timeout, **kwargs,
            )
            logger.debug('RG queued in %s %s %s', queue_name, func, job.id)
            return
        except Exception as error:
            logger.error('RQ-E %s %s %s', queue_name, func, error)
