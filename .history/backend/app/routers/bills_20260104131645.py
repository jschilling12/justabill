from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models import Bill, BillSection, BillStatus
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
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[BillStatus] = None,
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
    db: Session = Depends(get_db)
):
    """Get user's voting summary and support score for a bill"""
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


@router.post("/{bill_id}/resummarize")
async def resummarize_bill(bill_id: UUID, db: Session = Depends(get_db)):
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


@router.delete("/cleanup")
async def cleanup_old_bills(
    older_than_days: int = Query(60, ge=1, le=365, description="Delete bills not updated in X days"),
    dry_run: bool = Query(False, description="If true, return count without deleting"),
    db: Session = Depends(get_db)
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
