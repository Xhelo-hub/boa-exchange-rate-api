"""
Task scheduler for automated exchange rate updates
"""

import schedule
import time
import threading
from datetime import datetime
from typing import Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)

_scheduler_thread: Optional[threading.Thread] = None
_scheduler_running = False


def daily_update_task():
    """Daily task to update exchange rates"""
    try:
        logger.info("Starting daily exchange rate update task")
        
        # Import here to avoid circular imports
        from ..boa_scraper.scraper import BoAScraper
        from ..quickbooks.sync import QuickBooksSync
        from ..database.engine import get_db_manager
        from ..database.repository import ExchangeRateRepository
        
        # Scrape current rates
        scraper = BoAScraper()
        rates = scraper.get_current_rates()
        
        if rates:
            logger.info(f"Scraped {len(rates.rates)} exchange rates")
            
            # Save to database
            db_manager = get_db_manager()
            with db_manager.get_session() as session:
                repo = ExchangeRateRepository(session)
                stats = repo.save_rates(rates)
                logger.info(f"Database: {stats['new']} new, {stats['updated']} updated, {stats['unchanged']} unchanged")
            
            # Sync with QuickBooks (only priority currencies)
            qb_sync = QuickBooksSync()
            result = qb_sync.sync_rates(rates)
            
            if result:
                logger.info("Successfully synced rates with QuickBooks Online")
            else:
                logger.error("Failed to sync rates with QuickBooks Online")
        else:
            logger.warning("No exchange rates scraped")
            
    except Exception as e:
        logger.error(f"Error in daily update task: {str(e)}")


def run_scheduler():
    """Run the scheduler in a separate thread"""
    global _scheduler_running
    _scheduler_running = True
    
    logger.info("Starting scheduler thread")
    
    while _scheduler_running:
        schedule.run_pending()
        time.sleep(60)  # Check every minute
    
    logger.info("Scheduler thread stopped")


def start_scheduler(schedule_time: str = "09:00"):
    """
    Start the task scheduler
    
    Args:
        schedule_time: Time to run daily updates (HH:MM format)
    """
    global _scheduler_thread, _scheduler_running
    
    if _scheduler_thread and _scheduler_thread.is_alive():
        logger.warning("Scheduler is already running")
        return
    
    # Schedule daily task
    schedule.every().day.at(schedule_time).do(daily_update_task)
    
    logger.info(f"Scheduled daily updates at {schedule_time}")
    
    # Start scheduler thread
    _scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    _scheduler_thread.start()
    
    logger.info("Scheduler started")


def stop_scheduler():
    """Stop the task scheduler"""
    global _scheduler_running
    
    _scheduler_running = False
    schedule.clear()
    
    logger.info("Scheduler stopped")


def trigger_manual_update():
    """Trigger a manual update of exchange rates"""
    logger.info("Triggering manual exchange rate update")
    
    try:
        daily_update_task()
        return True
    except Exception as e:
        logger.error(f"Manual update failed: {str(e)}")
        return False