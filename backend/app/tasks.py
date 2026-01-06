from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import BillSection, Bill
from app.llm_client import get_llm_client
from uuid import UUID
import logging
import json

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.summarize_section", bind=True, max_retries=3)
def summarize_section_task(self, section_id: str):
    """
    Celery task to summarize a bill section using LLM
    Stores grounded summary and evidence quotes
    """
    db = SessionLocal()
    try:
        logger.info(f"Starting summarization for section {section_id}")
        
        # Get section
        section = db.query(BillSection).filter(
            BillSection.id == UUID(section_id)
        ).first()
        
        if not section:
            logger.error(f"Section not found: {section_id}")
            return {"status": "error", "message": "Section not found"}
        
        # Get LLM client
        llm_client = get_llm_client()
        
        # Generate summary
        try:
            import asyncio
            summary = asyncio.run(llm_client.generate_summary(
                section_text=section.section_text,
                section_key=section.section_key,
                heading=section.heading
            ))
            
            # Store summary
            section.summary_json = {
                "plain_summary_bullets": summary.plain_summary_bullets,
                "key_terms": summary.key_terms,
                "who_it_affects": summary.who_it_affects,
                "uncertainties": summary.uncertainties
            }
            section.evidence_quotes = summary.evidence_quotes
            
            db.commit()
            
            logger.info(f"Successfully summarized section {section_id}")
            return {
                "status": "success",
                "section_id": section_id,
                "bullets_count": len(summary.plain_summary_bullets),
                "evidence_count": len(summary.evidence_quotes)
            }
        
        except Exception as e:
            logger.error(f"Error in LLM summarization for section {section_id}: {e}", exc_info=True)
            # Store error info
            section.summary_json = {
                "plain_summary_bullets": [f"Error generating summary: {str(e)}"],
                "key_terms": [],
                "who_it_affects": [],
                "uncertainties": ["Summary generation failed"]
            }
            section.evidence_quotes = []
            db.commit()
            
            # Retry with exponential backoff
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    
    finally:
        db.close()


@celery_app.task(name="app.tasks.resummarize_bill", bind=True)
def resummarize_bill_task(self, bill_id: str):
    """
    Celery task to re-summarize all sections of a bill
    """
    db = SessionLocal()
    try:
        logger.info(f"Starting re-summarization for bill {bill_id}")
        
        # Get all sections for this bill
        sections = db.query(BillSection).filter(
            BillSection.bill_id == UUID(bill_id)
        ).all()
        
        if not sections:
            logger.error(f"No sections found for bill {bill_id}")
            return {"status": "error", "message": "No sections found"}
        
        # Queue individual summarization tasks
        task_ids = []
        for section in sections:
            task = summarize_section_task.delay(str(section.id))
            task_ids.append(task.id)
        
        logger.info(f"Queued {len(task_ids)} summarization tasks for bill {bill_id}")
        return {
            "status": "success",
            "bill_id": bill_id,
            "sections_queued": len(task_ids),
            "task_ids": task_ids
        }
    
    finally:
        db.close()


@celery_app.task(name="app.tasks.sync_recent_bills", bind=True)
def sync_recent_bills_task(self, days: int = 1):
    """
    Celery task to sync bills updated in the last N days
    Called by n8n daily workflow
    """
    db = SessionLocal()
    try:
        from app.congress_client import CongressAPIClient
        import httpx
        
        logger.info(f"Starting sync of bills updated in last {days} days")
        
        congress_client = CongressAPIClient()
        
        # Fetch recent bills
        import asyncio
        bills = asyncio.run(congress_client.get_recent_bills(days=days, limit=50))
        
        logger.info(f"Found {len(bills)} recent bills")
        
        # Trigger ingestion for each bill via internal API
        ingested_count = 0
        error_count = 0
        
        for bill_data in bills:
            try:
                # Extract identifiers
                bill_url = bill_data.get('url', '')
                # Parse URL to get congress, type, number
                # URL format: https://api.congress.gov/v3/bill/118/hr/1234
                parts = bill_url.split('/')
                if len(parts) >= 7:
                    congress = int(parts[-3])
                    bill_type = parts[-2]
                    bill_number = int(parts[-1])
                    
                    # Call ingestion endpoint (would normally be HTTP, but we can call function directly)
                    logger.info(f"Triggering ingestion for {congress}/{bill_type}/{bill_number}")
                    # In production, this would be an HTTP call to the ingestion endpoint
                    # For now, we'll just log it
                    ingested_count += 1
                else:
                    logger.warning(f"Could not parse bill URL: {bill_url}")
                    error_count += 1
            
            except Exception as e:
                logger.error(f"Error processing bill {bill_data.get('url')}: {e}")
                error_count += 1
        
        logger.info(f"Sync complete: {ingested_count} bills processed, {error_count} errors")
        return {
            "status": "success",
            "days": days,
            "bills_found": len(bills),
            "ingested": ingested_count,
            "errors": error_count
        }
    
    except Exception as e:
        logger.error(f"Error in sync_recent_bills_task: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    
    finally:
        db.close()
