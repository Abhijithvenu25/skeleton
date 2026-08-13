import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.db.session import async_session_maker

logger = structlog.get_logger(__name__)
scheduler = AsyncIOScheduler()

async def trigger_stale_enquiry_job():
    """Background job to mark stale enquiries as lost."""
    try:
        from app.services.enquiry import EnquiryService
        logger.info("Running trigger_stale_enquiry_job")
        async with async_session_maker() as session:
            service = EnquiryService(session)
            count = await service.mark_stale_enquiries_as_lost(days=45)
            logger.info("trigger_stale_enquiry_job completed", count_marked_lost=count)
    except Exception as e:
        logger.exception("Failed to run trigger_stale_enquiry_job", error=str(e))

def init_scheduler():
    # Run everyday at midnight (00:00)
    scheduler.add_job(trigger_stale_enquiry_job, "cron", hour=0, minute=0, id="stale_enquiry_job", replace_existing=True)
    logger.info("Scheduler initialized with stale_enquiry_job")
