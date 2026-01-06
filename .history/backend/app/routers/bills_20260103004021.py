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
    UserBillSummaryResponse
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
    db: Session = Depends(get_db)
):
    """List bills with pagination and optional filters"""
    
    query = db.query(Bill)
    
    # Apply filters
    if status:
        query = query.filter(Bill.status == status)
    if congress:
        query = query.filter(Bill.congress == congress)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    bills = query.order_by(desc(Bill.latest_action_date)).offset(offset).limit(page_size).all()
    
    # Calculate total pages
    pages = (total + page_size - 1) // page_size
    
    return PaginatedBillsResponse(
        items=bills,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


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
