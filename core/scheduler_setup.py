"""Scheduler setup for APScheduler."""

import logging

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from core.config import settings


def initialize_scheduler() -> BackgroundScheduler:
    """Initialize and start the APScheduler BackgroundScheduler.

    Returns:
        BackgroundScheduler: The initialized and started scheduler.

    Raises:
        Exception: If the scheduler fails to start.
    """
    logger = logging.getLogger(__name__)
    try:
        jobstores = {
            "default": SQLAlchemyJobStore(
                url=f"sqlite:///{settings.sqlite_db_path}", tablename="apscheduler_jobs"
            )
        }
        scheduler = BackgroundScheduler(jobstores=jobstores)
        scheduler.start()
        logger.info("BackgroundScheduler initialized and started.")
        return scheduler
    except Exception as e:
        logger.error("Error initializing BackgroundScheduler: %s", e)
        raise
