from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID
import hashlib
import logging

from app.database import get_db
from app.schemas import IngestBillRequest, IngestBillResponse
from app.models import Bill, BillVersion, BillSection, BillStatus
from app.congress_client import CongressAPIClient, BillTextFetcher, BillSectionizer

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/bill", response_model=IngestBillResponse)
async def ingest_bill(
    request: IngestBillRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Ingest a bill from Congress.gov API
    This endpoint is idempotent - if bill already exists, it will update if needed
    """
    
    try:
        # Initialize clients
        congress_client = CongressAPIClient()
        text_fetcher = BillTextFetcher()
        sectionizer = BillSectionizer()
        
        # Fetch bill metadata
        logger.info(f"Fetching bill {request.congress}/{request.bill_type}/{request.bill_number}")
        bill_data = await congress_client.get_bill(
            request.congress,
            request.bill_type,
            request.bill_number
        )
        
        if not bill_data:
            raise HTTPException(status_code=404, detail="Bill not found in Congress.gov API")
        
        # Check if bill already exists
        existing_bill = db.query(Bill).filter(
            Bill.congress == request.congress,
            Bill.bill_type == request.bill_type,
            Bill.bill_number == request.bill_number
        ).first()
        
        # Parse status from latest action
        latest_action = bill_data.get('latestAction', {})
        status_str = _map_status(latest_action)
        try:
            status = BillStatus(status_str)
        except ValueError:
            status = BillStatus.INTRODUCED
        
        # Skip bills that are only 'introduced' - we want bills actively moving through the process
        if status == BillStatus.INTRODUCED:
            logger.info(f"Skipping bill {request.bill_type.upper()} {request.bill_number} - status is 'introduced' (not actively progressing)")
            raise HTTPException(
                status_code=400,
                detail=f"Bill {request.bill_type.upper()} {request.bill_number} is only 'introduced' - not actively progressing through legislative process"
            )
        
        if existing_bill:
            bill = existing_bill
            # Update status if it changed
            if bill.status != status:
                bill.status = status
                db.add(bill)
                db.commit()
            logger.info(f"Bill already exists: {bill.id} (status: {status})")
        else:
            # Determine whether this is a primary law-making bill type (e.g., HR or S)
            bill_type_lower = (request.bill_type or "").lower()
            is_law_impact_candidate = bill_type_lower in {"hr", "s"}

            # Create new bill
            bill = Bill(
                congress=request.congress,
                bill_type=request.bill_type,
                bill_number=request.bill_number,
                title=bill_data.get('title'),
                introduced_date=bill_data.get('introducedDate'),
                latest_action_date=bill_data.get('latestAction', {}).get('actionDate'),
                status=status,
                sponsor=bill_data.get('sponsors', [{}])[0] if bill_data.get('sponsors') else None,
                source_urls={
                    'congress_gov': f"https://www.congress.gov/bill/{request.congress}th-congress/{request.bill_type}-bill/{request.bill_number}"
                },
                raw_metadata=bill_data,
                is_law_impact_candidate=is_law_impact_candidate,
            )
            db.add(bill)
            db.commit()
            db.refresh(bill)
            logger.info(f"Created new bill: {bill.id} (status: {status})")
        
        # Fetch text versions
        text_versions = await congress_client.get_bill_text_versions(
            request.congress,
            request.bill_type,
            request.bill_number
        )
        
        if not text_versions:
            logger.warning(f"No text versions found for bill {bill.id}")
            return IngestBillResponse(
                bill_id=bill.id,
                status="partial",
                message="Bill metadata ingested, but no text versions available yet",
                sections_created=0
            )
        
        # Select preferred text version (prefer HTML, then XML, then PDF)
        selected_version = None
        for version in text_versions:
            formats = version.get('formats', [])
            for fmt in formats:
                if fmt.get('type') in ['Formatted Text', 'HTML', 'XML']:
                    selected_version = {
                        'label': version.get('type'),
                        'url': fmt.get('url')
                    }
                    break
            if selected_version:
                break
        
        if not selected_version:
            logger.warning(f"No suitable text format found for bill {bill.id}")
            return IngestBillResponse(
                bill_id=bill.id,
                status="partial",
                message="Bill metadata ingested, but no suitable text format available",
                sections_created=0
            )
        
        # Fetch bill text
        logger.info(f"Fetching bill text from {selected_version['url']}")
        bill_text, content_hash = await text_fetcher.fetch_text(selected_version['url'])
        
        # Check if this version already exists
        existing_version = db.query(BillVersion).filter(
            BillVersion.bill_id == bill.id,
            BillVersion.content_hash == content_hash
        ).first()
        
        if existing_version:
            logger.info(f"Bill text unchanged (hash match): {content_hash}")
            # Count existing sections
            existing_sections_count = db.query(BillSection).filter(BillSection.bill_id == bill.id).count()
            return IngestBillResponse(
                bill_id=bill.id,
                status="unchanged",
                message="Bill text unchanged, no new sections created",
                sections_created=existing_sections_count
            )
        
        # Save bill version
        bill_version = BillVersion(
            bill_id=bill.id,
            version_label=selected_version['label'],
            source_url=selected_version['url'],
            content_hash=content_hash,
            raw_text=bill_text[:100000]  # Store first 100k chars
        )
        db.add(bill_version)
        
        # Sectionize bill text
        logger.info(f"Sectionizing bill text")
        sections_data = sectionizer.section_bill(bill_text)
        
        # Delete old sections if this is an update
        if existing_bill:
            db.query(BillSection).filter(BillSection.bill_id == bill.id).delete()
        
        # Create bill sections
        sections_created = 0
        for section_data in sections_data:
            section_text = section_data['text']
            section_text_hash = hashlib.sha256(section_text.encode('utf-8')).hexdigest()
            
            section = BillSection(
                bill_id=bill.id,
                section_key=section_data['section_key'],
                heading=section_data['heading'],
                order_index=section_data['order_index'],
                section_text=section_text,
                section_text_hash=section_text_hash,
                division=section_data.get('division'),
                title=section_data.get('title'),
                title_heading=section_data.get('title_heading')
            )
            db.add(section)
            sections_created += 1
        
        db.commit()
        logger.info(f"Created {sections_created} sections for bill {bill.id}")
        
        # Queue summarization tasks in background
        background_tasks.add_task(queue_summarization_tasks, bill.id)
        
        return IngestBillResponse(
            bill_id=bill.id,
            status="success",
            message=f"Bill ingested successfully with {sections_created} sections",
            sections_created=sections_created
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting bill: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error ingesting bill: {str(e)}")


@router.post("/bill/{bill_id}/backfill-groups")
async def backfill_groups(
    bill_id: UUID,
    db: Session = Depends(get_db)
):
    """Backfill division/title/title_heading for an already-ingested bill."""

    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    latest_version = (
        db.query(BillVersion)
        .filter(BillVersion.bill_id == bill_id)
        .order_by(BillVersion.fetched_at.desc())
        .first()
    )
    if not latest_version or not latest_version.source_url:
        raise HTTPException(status_code=400, detail="No bill version/source URL available to backfill")

    text_fetcher = BillTextFetcher()
    sectionizer = BillSectionizer()

    logger.info(f"Backfilling groups for bill {bill_id} using {latest_version.source_url}")
    bill_text, _content_hash = await text_fetcher.fetch_text(latest_version.source_url)
    sections_data = sectionizer.section_bill(bill_text)

    def normalize_section_key(key: str | None) -> str | None:
        if not key:
            return None
        normalized = " ".join(key.strip().upper().split())
        normalized = normalized.rstrip(".")
        return normalized

    incoming_by_section_key: dict[str, list[dict]] = {}
    for s in sections_data:
        k = normalize_section_key(s.get("section_key"))
        if not k:
            continue
        incoming_by_section_key.setdefault(k, []).append(s)

    sections = db.query(BillSection).filter(BillSection.bill_id == bill_id).all()
    updated = 0
    missing = 0
    for section in sections:
        section_key = normalize_section_key(section.section_key)
        candidates = incoming_by_section_key.get(section_key or "")
        if not candidates:
            missing += 1
            continue

        incoming = None
        if len(candidates) == 1:
            incoming = candidates[0]
        else:
            for c in candidates:
                if c.get("order_index") == section.order_index:
                    incoming = c
                    break
            if incoming is None:
                incoming = candidates[0]

        section.division = incoming.get("division")
        section.title = incoming.get("title")
        section.title_heading = incoming.get("title_heading")
        updated += 1

    db.commit()

    return {
        "bill_id": bill_id,
        "status": "success",
        "sections_total": len(sections),
        "sections_updated": updated,
        "sections_missing_match": missing,
    }


def queue_summarization_tasks(bill_id: UUID):
    """Queue Celery tasks to summarize all sections of a bill"""
    from app.tasks import summarize_section_task
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        sections = db.query(BillSection).filter(BillSection.bill_id == bill_id).all()
        for section in sections:
            summarize_section_task.delay(str(section.id))
        logger.info(f"Queued {len(sections)} summarization tasks for bill {bill_id}")
    finally:
        db.close()
