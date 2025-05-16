"""Scheduler setup for APScheduler."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler


def initialize_scheduler() -> BackgroundScheduler:
    """Initialize and start the APScheduler BackgroundScheduler.

    Returns:
        BackgroundScheduler: The initialized and started scheduler.

    Raises:
        Exception: If the scheduler fails to start.
    """
    logger = logging.getLogger(__name__)
    try:
        scheduler = BackgroundScheduler()
        scheduler.start()
        logger.info("BackgroundScheduler initialized and started.")
        return scheduler
    except Exception as e:
        logger.error("Error initializing BackgroundScheduler: %s", e)
        raise 