from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
import uuid

from app.database import get_db
from app.models import User, Vote, Bill, BillSection, VoteType
from app.schemas import VoteCreate, VoteResponse
from app.services.vote_service import VoteService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def get_current_user(
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db)
) -> User:
    """Get or create user based on session ID"""
    
    if not session_id:
        # Generate new session ID
        session_id = str(uuid.uuid4())
    
    # Find or create user
    user = db.query(User).filter(User.session_id == session_id).first()
    
    if not user:
        user = User(
            session_id=session_id,
            is_anonymous=1
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created new anonymous user: {user.id}")
    
    return user


@router.post("/vote", response_model=VoteResponse)
async def submit_vote(
    vote: VoteCreate,
    bill_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit a vote for a bill section"""
    
    # Verify bill exists
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Verify section exists and belongs to bill
    section = db.query(BillSection).filter(
        BillSection.id == vote.section_id,
        BillSection.bill_id == bill_id
    ).first()
    
    if not section:
        raise HTTPException(status_code=404, detail="Section not found or does not belong to this bill")
    
    # Check for existing vote
    existing_vote = db.query(Vote).filter(
        Vote.user_id == user.id,
        Vote.section_id == vote.section_id
    ).first()
    
    if existing_vote:
        # Update existing vote
        existing_vote.vote = vote.vote
        db.commit()
        db.refresh(existing_vote)
        logger.info(f"Updated vote for user {user.id}, section {vote.section_id}: {vote.vote}")
        
        # Invalidate cached summary
        from app.models import UserBillSummary
        db.query(UserBillSummary).filter(
            UserBillSummary.user_id == user.id,
            UserBillSummary.bill_id == bill_id
        ).delete()
        db.commit()
        
        return existing_vote
    else:
        # Create new vote
        new_vote = Vote(
            user_id=user.id,
            bill_id=bill_id,
            section_id=vote.section_id,
            vote=vote.vote
        )
        db.add(new_vote)
        db.commit()
        db.refresh(new_vote)
        logger.info(f"Created vote for user {user.id}, section {vote.section_id}: {vote.vote}")
        
        return new_vote


@router.post("/bulk-vote")
async def submit_bulk_votes(
    bill_id: UUID,
    votes: List[VoteCreate],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit multiple votes at once"""
    
    # Verify bill exists
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Get all section IDs for this bill
    section_ids = [v.section_id for v in votes]
    sections = db.query(BillSection).filter(
        BillSection.id.in_(section_ids),
        BillSection.bill_id == bill_id
    ).all()
    
    if len(sections) != len(votes):
        raise HTTPException(status_code=400, detail="Some sections not found or do not belong to this bill")
    
    # Get existing votes
    existing_votes = db.query(Vote).filter(
        Vote.user_id == user.id,
        Vote.section_id.in_(section_ids)
    ).all()
    existing_votes_dict = {v.section_id: v for v in existing_votes}
    
    # Update or create votes
    created_count = 0
    updated_count = 0
    
    for vote in votes:
        if vote.section_id in existing_votes_dict:
            # Update
            existing_votes_dict[vote.section_id].vote = vote.vote
            updated_count += 1
        else:
            # Create
            new_vote = Vote(
                user_id=user.id,
                bill_id=bill_id,
                section_id=vote.section_id,
                vote=vote.vote
            )
            db.add(new_vote)
            created_count += 1
    
    # Invalidate cached summary
    from app.models import UserBillSummary
    db.query(UserBillSummary).filter(
        UserBillSummary.user_id == user.id,
        UserBillSummary.bill_id == bill_id
    ).delete()
    
    db.commit()
    
    logger.info(f"Bulk vote: {created_count} created, {updated_count} updated for user {user.id}, bill {bill_id}")
    
    return {
        "message": "Votes submitted successfully",
        "created": created_count,
        "updated": updated_count,
        "total": len(votes)
    }


@router.get("/my-votes/{bill_id}")
async def get_my_votes(
    bill_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's votes for a bill"""
    
    votes = db.query(Vote).filter(
        Vote.user_id == user.id,
        Vote.bill_id == bill_id
    ).all()
    
    return {
        "bill_id": bill_id,
        "user_id": user.id,
        "votes": [{"section_id": v.section_id, "vote": v.vote} for v in votes]
    }
