from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime, timedelta
import os
from supabase import create_client
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Supabase
supabase = create_client(
    os.environ.get('SUPABASE_URL'),
    os.environ.get('SUPABASE_ANON_KEY')
)

# Initialize scheduler
scheduler = BlockingScheduler()

@scheduler.scheduled_job('interval', hours=6)
def log_stats():
    """Log content statistics every 6 hours"""
    try:
        # Get total content count
        result = supabase.table('cms_content').select('id', count='exact').execute()
        total_count = result.count if result.count else 0

        logger.info(f"Total content items: {total_count}")

        # Get file count
        file_result = supabase.table('cms_content')\
            .select('id', count='exact')\
            .eq('content_type', 'file')\
            .execute()
        file_count = file_result.count if file_result.count else 0

        logger.info(f"Total file uploads: {file_count}")

        # Log to activity table
        supabase.table('cms_activity_log').insert({
            'action': 'stats_generated',
            'details': f'Total items: {total_count}, Files: {file_count}'
        }).execute()

        logger.info("Stats logged successfully")

    except Exception as e:
        logger.error(f"Error in stats job: {str(e)}")

@scheduler.scheduled_job('interval', hours=24)
def cleanup_old_activity_logs():
    """Clean up activity logs older than 90 days"""
    try:
        # Calculate date 90 days ago
        cutoff_date = (datetime.now() - timedelta(days=90)).isoformat()

        # Delete old logs
        result = supabase.table('cms_activity_log')\
            .delete()\
            .lt('created_at', cutoff_date)\
            .execute()

        logger.info(f"Cleaned up activity logs older than 90 days")

    except Exception as e:
        logger.error(f"Error in cleanup job: {str(e)}")

if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("Goldco CMS Worker Started")
    logger.info("=" * 50)
    logger.info("Scheduled jobs:")
    logger.info("  - Stats logging: Every 6 hours")
    logger.info("  - Activity log cleanup: Every 24 hours")
    logger.info("=" * 50)

    # Run stats job immediately on startup
    logger.info("Running initial stats collection...")
    log_stats()

    # Start the scheduler
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker stopped")
