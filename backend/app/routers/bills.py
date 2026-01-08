from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models import Bill, BillSection, BillStatus
from app.auth import get_current_user_auth, require_admin_key
from app.schemas import (
    BillResponse,
    BillWithSections,
    PaginatedBillsResponse,
    UserBillSummaryResponse,
    BillPopularityUpdate,
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=PaginatedBillsResponse)
async def list_bills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    status: Optional[BillStatus] = None,
    exclude_status: Optional[BillStatus] = Query(
        None,
        description="Exclude bills with this status (e.g., 'enacted' to exclude signed laws)",
    ),
    congress: Optional[int] = None,
    popular: Optional[bool] = Query(None, description="If true, only return bills marked as popular"),
    law_impact_only: Optional[bool] = Query(
        None,
        description="If true, only return bills that are primary law-making vehicles (e.g., HR/S)",
    ),
    db: Session = Depends(get_db)
):
    """List bills with pagination and optional filters"""
    
    query = db.query(Bill)
    
    # Apply filters
    if status:
        query = query.filter(Bill.status == status)
    if exclude_status:
        query = query.filter(Bill.status != exclude_status)
    if congress:
        query = query.filter(Bill.congress == congress)
    if popular is True:
        query = query.filter(Bill.is_popular.is_(True))
    if law_impact_only is True:
        query = query.filter(Bill.is_law_impact_candidate.is_(True))
    
    # Get total count
    total = query.count()

    # Apply pagination and ordering
    offset = (page - 1) * page_size
    if popular is True:
        bills = (
            query.order_by(desc(Bill.popularity_score), desc(Bill.latest_action_date))
            .offset(offset)
            .limit(page_size)
            .all()
        )
    else:
        bills = (
            query.order_by(desc(Bill.latest_action_date))
            .offset(offset)
            .limit(page_size)
            .all()
        )
    
    # Calculate total pages
    pages = (total + page_size - 1) // page_size
    
    return PaginatedBillsResponse(
        items=bills,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.patch("/{bill_id}/popularity", response_model=BillResponse)
async def update_bill_popularity(
    bill_id: UUID,
    payload: BillPopularityUpdate,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    """Update popularity fields for a bill (for automation like n8n)."""
    from datetime import datetime, timezone

    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    changed = False
    if payload.is_popular is not None:
        bill.is_popular = payload.is_popular
        changed = True
    if payload.popularity_score is not None:
        bill.popularity_score = payload.popularity_score
        changed = True

    if changed:
        bill.popularity_updated_at = datetime.now(timezone.utc)
        db.add(bill)
        db.commit()
        db.refresh(bill)

    return bill


@router.patch("/lookup/{congress}/{bill_type}/{bill_number}/popularity", response_model=BillResponse)
async def update_bill_popularity_by_lookup(
    congress: int,
    bill_type: str,
    bill_number: int,
    payload: BillPopularityUpdate,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    """Update popularity fields for a bill by congress/type/number (for n8n automation)."""
    from datetime import datetime, timezone

    bill = db.query(Bill).filter(
        Bill.congress == congress,
        Bill.bill_type == bill_type.lower(),
        Bill.bill_number == bill_number
    ).first()
    
    if not bill:
        raise HTTPException(
            status_code=404, 
            detail=f"Bill not found: {bill_type.upper()} {bill_number} ({congress}th Congress)"
        )

    changed = False
    if payload.is_popular is not None:
        bill.is_popular = payload.is_popular
        changed = True
    if payload.popularity_score is not None:
        bill.popularity_score = payload.popularity_score
        changed = True

    if changed:
        bill.popularity_updated_at = datetime.now(timezone.utc)
        db.add(bill)
        db.commit()
        db.refresh(bill)

    return bill


# NOTE: This route MUST be defined before /{bill_id} routes to avoid being captured by the UUID pattern
@router.get("/popular-by-president")
async def get_popular_bills_by_president(
    top_n: int = Query(2, ge=1, le=10, description="Number of top bills per president"),
    db: Session = Depends(get_db)
):
    """Get the most popular enacted bills for each president based on external popularity scores"""
    from datetime import datetime
    
    # President date ranges for grouping - corrected for Trump 1st vs 2nd term
    PRESIDENT_RANGES = {
        "Donald Trump 2nd": ("2025-01-20", "2029-01-20"),
        "Joe Biden": ("2021-01-20", "2025-01-20"),
        "Donald Trump": ("2017-01-20", "2021-01-20"),
        "Barack Obama": ("2009-01-20", "2017-01-20"),
        "George W. Bush": ("2001-01-20", "2009-01-20"),
        "Bill Clinton": ("1993-01-20", "2001-01-20"),
        "George H.W. Bush": ("1989-01-20", "1993-01-20"),
    }
    
    result = {}
    
    for president, (start_str, end_str) in PRESIDENT_RANGES.items():
        start_date = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
        
        # Get enacted bills in this president's term, ordered by popularity_score
        popular_bills = (
            db.query(Bill)
            .filter(Bill.status == BillStatus.ENACTED)
            .filter(Bill.latest_action_date >= start_date.date())
            .filter(Bill.latest_action_date < end_date.date())
            .filter(Bill.popularity_score > 0)  # Only include bills with external popularity data
            .order_by(desc(Bill.popularity_score))
            .limit(top_n)
            .all()
        )
        
        if popular_bills:
            result[president] = [
                {
                    "bill_id": str(bill.id),
                    "bill_type": bill.bill_type,
                    "bill_number": bill.bill_number,
                    "title": bill.title,
                    "popularity_score": bill.popularity_score,
                    "latest_action_date": bill.latest_action_date.isoformat() if bill.latest_action_date else None,
                }
                for bill in popular_bills
            ]
    
    return result


@router.get("/{bill_id}", response_model=BillWithSections)
async def get_bill(bill_id: UUID, db: Session = Depends(get_db)):
    """Get a bill by ID with all its sections"""
    
    bill = db.query(Bill).options(
        joinedload(Bill.sections)
    ).filter(Bill.id == bill_id).first()
    
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Sort sections by order_index
    bill.sections.sort(key=lambda s: s.order_index)
    
    return bill


@router.get("/{bill_id}/user-summary", response_model=UserBillSummaryResponse)
async def get_user_bill_summary(
    bill_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_auth),
):
    """Get user's voting summary and support score for a bill"""
    # Prevent cross-user access. Use /my-summary for the normal flow.
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    from app.models import UserBillSummary, Vote, VoteType
    from app.services.vote_service import VoteService
    
    # Check if bill exists
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Check if summary already exists
    summary = db.query(UserBillSummary).filter(
        UserBillSummary.user_id == user_id,
        UserBillSummary.bill_id == bill_id
    ).first()
    
    if not summary:
        # Generate new summary
        vote_service = VoteService(db)
        summary = vote_service.generate_user_bill_summary(user_id, bill_id)
    
    return summary


@router.get("/{bill_id}/my-summary", response_model=UserBillSummaryResponse)
async def get_my_bill_summary(
    bill_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_auth),
):
    """Get authenticated user's voting summary for a bill."""
    from app.models import UserBillSummary
    from app.services.vote_service import VoteService

    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    summary = db.query(UserBillSummary).filter(
        UserBillSummary.user_id == current_user.id,
        UserBillSummary.bill_id == bill_id,
    ).first()

    if not summary:
        vote_service = VoteService(db)
        summary = vote_service.generate_user_bill_summary(current_user.id, bill_id)

    return summary


@router.post("/{bill_id}/resummarize")
async def resummarize_bill(
    bill_id: UUID,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    """Trigger re-summarization of all sections in a bill"""
    from app.tasks import resummarize_bill_task
    
    # Check if bill exists
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Trigger async task
    task = resummarize_bill_task.delay(str(bill_id))
    
    return {
        "message": "Re-summarization task queued",
        "bill_id": bill_id,
        "task_id": task.id
    }


@router.post("/resummarize-failed")
async def resummarize_failed_sections(
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    """Find all sections with failed summaries and queue them for re-summarization"""
    from app.tasks import summarize_section_task
    from sqlalchemy import cast, String
    
    # Find sections where summary_json contains "Error generating"
    failed_sections = db.query(BillSection).filter(
        cast(BillSection.summary_json, String).like('%Error generating%')
    ).all()
    
    # Also find sections with no summary at all
    null_sections = db.query(BillSection).filter(
        BillSection.summary_json.is_(None)
    ).all()
    
    all_sections = failed_sections + null_sections
    
    if not all_sections:
        return {
            "message": "No failed or missing summaries found",
            "queued": 0
        }
    
    # Queue summarization tasks
    task_ids = []
    for section in all_sections:
        task = summarize_section_task.delay(str(section.id))
        task_ids.append(task.id)
    
    return {
        "message": f"Queued {len(task_ids)} sections for re-summarization",
        "queued": len(task_ids),
        "failed_count": len(failed_sections),
        "null_count": len(null_sections),
        "task_ids": task_ids[:10]  # Return first 10 task IDs
    }


@router.delete("/cleanup")
async def cleanup_old_bills(
    older_than_days: int = Query(60, ge=1, le=365, description="Delete bills not updated in X days"),
    dry_run: bool = Query(False, description="If true, return count without deleting"),
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    """Remove bills that haven't been updated recently (for data freshness)"""
    from datetime import datetime, timedelta, timezone
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    
    # Find bills to delete
    old_bills_query = db.query(Bill).filter(Bill.updated_at < cutoff_date)
    count = old_bills_query.count()
    
    if dry_run:
        return {
            "dry_run": True,
            "bills_to_delete": count,
            "cutoff_date": cutoff_date.isoformat(),
            "older_than_days": older_than_days
        }
    
    # Delete old bills (CASCADE will delete related sections, votes, evidence, etc.)
    deleted = old_bills_query.delete(synchronize_session=False)
    db.commit()
    
    logger.info(f"Deleted {deleted} bills older than {older_than_days} days (cutoff: {cutoff_date})")
    
    return {
        "deleted": deleted,
        "cutoff_date": cutoff_date.isoformat(),
        "older_than_days": older_than_days
    }


@router.post("/update-popularity")
async def update_bill_popularity(
    bill_updates: List[dict],
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    """
    Update popularity scores for bills (called by n8n after web search).
    Expects: [{"bill_id": "uuid", "popularity_score": 123}, ...]
    """
    from datetime import datetime, timezone
    
    updated_count = 0
    errors = []
    
    for update in bill_updates:
        try:
            bill_id = UUID(update.get("bill_id"))
            score = int(update.get("popularity_score", 0))
            
            bill = db.query(Bill).filter(Bill.id == bill_id).first()
            if bill:
                bill.popularity_score = score
                bill.popularity_updated_at = datetime.now(timezone.utc)
                bill.is_popular = score > 50  # Mark as popular if score > 50
                updated_count += 1
            else:
                errors.append(f"Bill {bill_id} not found")
        except Exception as e:
            errors.append(f"Error updating bill {update.get('bill_id')}: {str(e)}")
    
    db.commit()
    
    return {
        "updated": updated_count,
        "total": len(bill_updates),
        "errors": errors if errors else None
    }
