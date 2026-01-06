from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from uuid import UUID
import uuid
from sqlalchemy import func

from app.database import get_db
from app.models import User, Vote, Bill, BillSection, VoteType
from app.schemas import (
    VoteCreate,
    VoteResponse,
    VoteSubmitResponse,
    VoteStatsResponse,
    VoteStatsWithSegmentsResponse,
    VoteCounts,
    VotePercents,
    SegmentStats,
    MyBillsVotesResponse,
    MyBillVoteItem,
    BillSectionVoteStatsResponse,
    SectionVoteStatsItem,
)
from app.services.vote_service import VoteService
from app.auth import get_current_user_auth, get_optional_user_auth
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


def _counts_and_percents(up: int, down: int, skip: int) -> tuple[VoteCounts, VotePercents]:
    total = up + down + skip
    if total <= 0:
        return VoteCounts(up=0, down=0, skip=0, total=0), VotePercents(agree_pct=0.0, disagree_pct=0.0)
    agree_pct = (up / total) * 100.0
    disagree_pct = (down / total) * 100.0
    return VoteCounts(up=up, down=down, skip=skip, total=total), VotePercents(agree_pct=agree_pct, disagree_pct=disagree_pct)


@router.post("/vote", response_model=VoteSubmitResponse)
async def submit_vote(
    vote: VoteCreate,
    bill_id: UUID,
    user: User = Depends(get_current_user_auth),
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
        
        return VoteSubmitResponse(vote=existing_vote, updated=True)
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
        return VoteSubmitResponse(vote=new_vote, updated=False)


@router.post("/bulk-vote")
async def submit_bulk_votes(
    bill_id: UUID,
    votes: List[VoteCreate],
    user: User = Depends(get_current_user_auth),
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
    user: User = Depends(get_current_user_auth),
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


@router.get("/my-bills", response_model=MyBillsVotesResponse)
async def get_my_bills_votes(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_auth),
):
    # Return bills the user has voted on (distinct by bill), along with count of voted sections.
    from app.models import Bill

    rows = (
        db.query(
            Vote.bill_id,
            func.count(func.distinct(Vote.section_id)).label("voted_sections"),
            Bill.congress,
            Bill.bill_type,
            Bill.bill_number,
            Bill.title,
            Bill.latest_action_date,
        )
        .join(Bill, Bill.id == Vote.bill_id)
        .filter(Vote.user_id == user.id)
        .group_by(
            Vote.bill_id,
            Bill.congress,
            Bill.bill_type,
            Bill.bill_number,
            Bill.title,
            Bill.latest_action_date,
        )
        .order_by(func.max(Vote.updated_at).desc())
        .all()
    )

    items = [
        MyBillVoteItem(
            bill_id=row[0],
            voted_sections=int(row[1]),
            congress=row[2],
            bill_type=row[3],
            bill_number=row[4],
            title=row[5],
            latest_action_date=row[6],
        )
        for row in rows
    ]

    return MyBillsVotesResponse(items=items)


@router.get("/bill/{bill_id}/stats", response_model=VoteStatsResponse)
async def get_bill_vote_stats(bill_id: UUID, db: Session = Depends(get_db)):
    rows = (
        db.query(Vote.vote, func.count(Vote.id))
        .filter(Vote.bill_id == bill_id)
        .group_by(Vote.vote)
        .all()
    )
    counts: Dict[str, int] = {v.value: 0 for v in VoteType}
    for vote_type, count in rows:
        counts[vote_type.value] = int(count)

    c, p = _counts_and_percents(counts["up"], counts["down"], counts["skip"])
    return VoteStatsResponse(counts=c, percents=p)


@router.get("/bill/{bill_id}/section-stats", response_model=BillSectionVoteStatsResponse)
async def get_bill_section_vote_stats(bill_id: UUID, db: Session = Depends(get_db)):
    rows = (
        db.query(Vote.section_id, Vote.vote, func.count(Vote.id))
        .filter(Vote.bill_id == bill_id)
        .group_by(Vote.section_id, Vote.vote)
        .all()
    )

    by_section: Dict[UUID, Dict[str, int]] = {}
    for section_id, vote_type, count in rows:
        if section_id not in by_section:
            by_section[section_id] = {"up": 0, "down": 0, "skip": 0}
        by_section[section_id][vote_type.value] += int(count)

    items: List[SectionVoteStatsItem] = []
    for section_id, cdict in by_section.items():
        counts, percents = _counts_and_percents(cdict["up"], cdict["down"], cdict["skip"])
        items.append(SectionVoteStatsItem(section_id=section_id, counts=counts, percents=percents))

    return BillSectionVoteStatsResponse(bill_id=bill_id, items=items)


@router.get("/section/{section_id}/stats", response_model=VoteStatsResponse)
async def get_section_vote_stats(section_id: UUID, db: Session = Depends(get_db)):
    rows = (
        db.query(Vote.vote, func.count(Vote.id))
        .filter(Vote.section_id == section_id)
        .group_by(Vote.vote)
        .all()
    )
    counts: Dict[str, int] = {v.value: 0 for v in VoteType}
    for vote_type, count in rows:
        counts[vote_type.value] = int(count)

    c, p = _counts_and_percents(counts["up"], counts["down"], counts["skip"])
    return VoteStatsResponse(counts=c, percents=p)


@router.get("/bill/{bill_id}/stats/segments", response_model=VoteStatsWithSegmentsResponse)
async def get_bill_vote_stats_segments(
    bill_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_auth),
):
    # Opt-in required to view segmented data
    if not current_user.affiliation_raw:
        raise HTTPException(status_code=403, detail="Affiliation opt-in required")

    overall = await get_bill_vote_stats(bill_id=bill_id, db=db)

    seg_rows = (
        db.query(User.affiliation_bucket, Vote.vote, func.count(Vote.id))
        .join(User, User.id == Vote.user_id)
        .filter(Vote.bill_id == bill_id)
        .group_by(User.affiliation_bucket, Vote.vote)
        .all()
    )

    buckets = ["republican", "liberal", "other"]
    bucket_counts: Dict[str, Dict[str, int]] = {b: {"up": 0, "down": 0, "skip": 0} for b in buckets}
    for bucket, vote_type, count in seg_rows:
        b = (bucket or "other")
        if b not in bucket_counts:
            b = "other"
        bucket_counts[b][vote_type.value] += int(count)

    segments: List[SegmentStats] = []
    for b in buckets:
        c, p = _counts_and_percents(bucket_counts[b]["up"], bucket_counts[b]["down"], bucket_counts[b]["skip"])
        segments.append(SegmentStats(bucket=b, counts=c, percents=p))

    return VoteStatsWithSegmentsResponse(counts=overall.counts, percents=overall.percents, segments=segments)


@router.get("/section/{section_id}/stats/segments", response_model=VoteStatsWithSegmentsResponse)
async def get_section_vote_stats_segments(
    section_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_auth),
):
    if not current_user.affiliation_raw:
        raise HTTPException(status_code=403, detail="Affiliation opt-in required")

    overall = await get_section_vote_stats(section_id=section_id, db=db)

    seg_rows = (
        db.query(User.affiliation_bucket, Vote.vote, func.count(Vote.id))
        .join(User, User.id == Vote.user_id)
        .filter(Vote.section_id == section_id)
        .group_by(User.affiliation_bucket, Vote.vote)
        .all()
    )

    buckets = ["republican", "liberal", "other"]
    bucket_counts: Dict[str, Dict[str, int]] = {b: {"up": 0, "down": 0, "skip": 0} for b in buckets}
    for bucket, vote_type, count in seg_rows:
        b = (bucket or "other")
        if b not in bucket_counts:
            b = "other"
        bucket_counts[b][vote_type.value] += int(count)

    segments: List[SegmentStats] = []
    for b in buckets:
        c, p = _counts_and_percents(bucket_counts[b]["up"], bucket_counts[b]["down"], bucket_counts[b]["skip"])
        segments.append(SegmentStats(bucket=b, counts=c, percents=p))

    return VoteStatsWithSegmentsResponse(counts=overall.counts, percents=overall.percents, segments=segments)
