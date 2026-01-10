from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID
import hashlib
import logging

from app.database import get_db
from app.schemas import IngestBillRequest, IngestBillResponse
from app.models import Bill, BillVersion, BillSection, BillStatus
from app.congress_client import CongressAPIClient, BillTextFetcher, BillSectionizer
from app.auth import require_admin_key

logger = logging.getLogger(__name__)
router = APIRouter()


# Map bill_type codes to Congress.gov URL format
BILL_TYPE_URL_MAP = {
    'hr': 'house-bill',
    's': 'senate-bill',
    'hjres': 'house-joint-resolution',
    'sjres': 'senate-joint-resolution',
    'hconres': 'house-concurrent-resolution',
    'sconres': 'senate-concurrent-resolution',
    'hres': 'house-resolution',
    'sres': 'senate-resolution',
}


def _get_congress_gov_url(congress: int, bill_type: str, bill_number: int) -> str:
    """Generate correct Congress.gov URL for a bill"""
    url_bill_type = BILL_TYPE_URL_MAP.get(bill_type.lower(), f"{bill_type.lower()}-bill")
    return f"https://www.congress.gov/bill/{congress}th-congress/{url_bill_type}/{bill_number}"


def _map_status(latest_action: dict, all_actions: list = None) -> str:
    """
    Map Congress.gov actions to our BillStatus enum.
    Uses all actions history for accuracy, not just latest action.
    """
    # Collect all action text for analysis
    all_action_texts = []
    
    # Add latest action
    if latest_action:
        all_action_texts.append((latest_action.get('text') or '').lower())
    
    # Add all historical actions if provided
    if all_actions:
        for action in all_actions:
            all_action_texts.append((action.get('text') or '').lower())
    
    # Join all text for comprehensive search
    combined_text = ' '.join(all_action_texts)
    
    # Check for enacted/law (highest priority)
    if 'became public law' in combined_text or 'became law' in combined_text:
        return 'enacted'
    
    # Check for vetoed
    if 'veto' in combined_text and 'override' not in combined_text:
        return 'vetoed'
    
    # Check for passed both chambers
    passed_house = any(
        'passed house' in t or 'agreed to in house' in t or 
        'on passage passed' in t and 'house' in t
        for t in all_action_texts
    )
    passed_senate = any(
        'passed senate' in t or 'agreed to in senate' in t or
        'on passage passed' in t and 'senate' in t
        for t in all_action_texts
    )
    
    if passed_house and passed_senate:
        return 'passed_both'
    
    # Check for conference
    if 'conference' in combined_text:
        return 'in_conference'
    
    # Check for passed Senate only
    if passed_senate:
        return 'passed_senate'
    
    # Check for passed House only
    if passed_house:
        return 'passed_house'
    
    # Check for Senate activity (bill originated in House and moved to Senate)
    senate_activity = any(
        action.get('sourceSystem', {}).get('name') == 'Senate'
        for action in (all_actions or [])
    )
    if senate_activity:
        # If there's Senate activity, the bill likely passed the House
        return 'passed_house'
    
    # Check for committee action
    if 'committee' in combined_text or 'referred to' in combined_text:
        return 'in_committee'
    
    # Default to introduced
    return 'introduced'


@router.post("/bill", response_model=IngestBillResponse)
async def ingest_bill(
    request: IngestBillRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
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
        
        # Fetch all actions for better status detection
        logger.info(f"Fetching bill actions for accurate status detection")
        all_actions = await congress_client.get_bill_actions(
            request.congress,
            request.bill_type,
            request.bill_number
        )
        
        # Check if bill already exists
        existing_bill = db.query(Bill).filter(
            Bill.congress == request.congress,
            Bill.bill_type == request.bill_type,
            Bill.bill_number == request.bill_number
        ).first()
        
        # Use force_status if provided, otherwise parse from actions
        if request.force_status:
            status = request.force_status
            logger.info(f"Using forced status: {status}")
        else:
            # Parse status from latest action + all actions
            latest_action = bill_data.get('latestAction', {})
            status_str = _map_status(latest_action, all_actions)
            logger.info(f"Detected status from actions: {status_str}")
            try:
                status = BillStatus(status_str)
            except ValueError:
                status = BillStatus.INTRODUCED
        
        # Skip bills that are only 'introduced' - we want bills actively moving through the process
        # BUT allow through if force_status is set (e.g., for enacted bills workflow)
        if status == BillStatus.INTRODUCED and not request.force_status:
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
                    'congress_gov': _get_congress_gov_url(request.congress, request.bill_type, request.bill_number)
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
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
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


# President to Congress mapping for on-demand fetching
PRESIDENT_CONGRESS_MAP = {
    "Donald Trump 2nd": {"start": 115, "end": 119, "years": "2017-2021, 2025-2029"},
    "Joe Biden": {"start": 117, "end": 118, "years": "2021-2025"},
    "Barack Obama": {"start": 111, "end": 114, "years": "2009-2017"},
    "George W. Bush": {"start": 107, "end": 110, "years": "2001-2009"},
    "Bill Clinton": {"start": 103, "end": 106, "years": "1993-2001"},
    "George H.W. Bush": {"start": 101, "end": 102, "years": "1989-1993"},
}


@router.post("/fetch-enacted-by-president")
async def fetch_enacted_by_president(
    president_name: str,
    _admin: None = Depends(require_admin_key),
):
    """
    Trigger n8n workflow to fetch enacted bills for a specific president's term.
    This calls the n8n webhook which then fetches and ingests the bills.
    """
    import httpx
    import os
    
    # Normalize the president name for lookup
    # Handle "Donald Trump" appearing twice (both terms)
    lookup_name = president_name
    
    if president_name not in PRESIDENT_CONGRESS_MAP:
        # Try to find a partial match
        for key in PRESIDENT_CONGRESS_MAP:
            if president_name in key or key in president_name:
                lookup_name = key
                break
    
    if lookup_name not in PRESIDENT_CONGRESS_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown president: {president_name}. Available: {list(PRESIDENT_CONGRESS_MAP.keys())}"
        )
    
    congress_range = PRESIDENT_CONGRESS_MAP[lookup_name]
    
    # Get n8n webhook URL and auth from environment
    n8n_webhook_url = os.getenv("N8N_ENACTED_WEBHOOK_URL")
    n8n_webhook_auth = os.getenv("N8N_WEBHOOK_AUTH_KEY", "")
    if not n8n_webhook_url:
        raise HTTPException(
            status_code=500,
            detail="N8N_ENACTED_WEBHOOK_URL not configured"
        )
    
    try:
        headers = {}
        if n8n_webhook_auth:
            headers["Authorization"] = f"Bearer {n8n_webhook_auth}"
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                n8n_webhook_url,
                json={
                    "president_name": lookup_name,
                    "start_congress": congress_range["start"],
                    "end_congress": congress_range["end"],
                },
                headers=headers
            )
            
            if response.status_code >= 400:
                logger.error(f"n8n webhook error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=502,
                    detail=f"n8n workflow failed: {response.text}"
                )
            
            result = response.json() if response.text else {}
            
            return {
                "status": "triggered",
                "president": lookup_name,
                "congress_range": congress_range,
                "n8n_result": result,
            }
            
    except httpx.TimeoutException:
        # The workflow might still be running, which is fine
        return {
            "status": "triggered_async",
            "president": lookup_name,
            "congress_range": congress_range,
            "message": "Workflow triggered but response timed out. Bills will be ingested in the background.",
        }
    except Exception as e:
        logger.error(f"Error triggering n8n workflow: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger n8n workflow: {str(e)}"
        )
