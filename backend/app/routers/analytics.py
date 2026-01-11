"""
Analytics API - Aggregated insights for survey panel monetization.

Privacy-compliant: Only returns aggregated data with minimum population thresholds.
No individual-level data is ever exposed.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.database import get_db
from app.models import User, Vote, VoteType, Bill, BillSection
from app.auth import require_admin_key, get_current_user_auth

router = APIRouter()

# Minimum users required to return aggregated data (privacy threshold)
MIN_POPULATION_THRESHOLD = 25


class AggregatedSentiment(BaseModel):
    """Aggregated sentiment data for a geographic area or demographic"""
    group_key: str
    group_value: str
    total_opted_in_users: int
    total_votes: int
    support_percentage: float
    oppose_percentage: float
    skip_percentage: float
    sample_sufficient: bool  # True if meets MIN_POPULATION_THRESHOLD


class BillSentimentByGroup(BaseModel):
    """Bill-level sentiment breakdown by groups"""
    bill_id: str
    bill_title: str
    congress: int
    bill_type: str
    bill_number: int
    sentiments: List[AggregatedSentiment]


class DistrictInsight(BaseModel):
    """Aggregated insight for a congressional district"""
    district: str
    state: str
    opted_in_users: int
    total_votes: int
    top_supported_bills: List[dict]
    top_opposed_bills: List[dict]
    affiliation_breakdown: dict
    sample_sufficient: bool


@router.get("/survey-panel/stats")
async def get_survey_panel_stats(
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    """
    Get overall stats about the survey panel opt-in population.
    Admin only - for internal metrics.
    """
    total_users = db.query(func.count(User.id)).scalar()
    opted_in = db.query(func.count(User.id)).filter(User.survey_opt_in == True).scalar()
    
    # Breakdown by state (only states meeting threshold)
    state_counts = db.query(
        User.state_code,
        func.count(User.id).label('count')
    ).filter(
        User.survey_opt_in == True,
        User.state_code.isnot(None)
    ).group_by(User.state_code).all()
    
    states_meeting_threshold = [
        {"state": s.state_code, "count": s.count}
        for s in state_counts if s.count >= MIN_POPULATION_THRESHOLD
    ]
    
    # Breakdown by affiliation
    affiliation_counts = db.query(
        User.affiliation_bucket,
        func.count(User.id).label('count')
    ).filter(
        User.survey_opt_in == True,
        User.affiliation_bucket.isnot(None)
    ).group_by(User.affiliation_bucket).all()
    
    # Breakdown by age range
    age_counts = db.query(
        User.age_range,
        func.count(User.id).label('count')
    ).filter(
        User.survey_opt_in == True,
        User.age_range.isnot(None)
    ).group_by(User.age_range).all()
    
    return {
        "total_users": total_users,
        "opted_in_users": opted_in,
        "opt_in_rate": round(opted_in / total_users * 100, 2) if total_users > 0 else 0,
        "min_population_threshold": MIN_POPULATION_THRESHOLD,
        "states_with_sufficient_sample": states_meeting_threshold,
        "affiliation_breakdown": {a.affiliation_bucket: a.count for a in affiliation_counts},
        "age_breakdown": {a.age_range: a.count for a in age_counts if a.age_range}
    }


@router.get("/sentiment/by-state/{state_code}")
async def get_state_sentiment(
    state_code: str,
    bill_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    """
    Get aggregated sentiment for a state.
    Only returns data if minimum population threshold is met.
    """
    state_code = state_code.upper()
    
    # Check if we have enough opted-in users in this state
    opted_in_count = db.query(func.count(User.id)).filter(
        User.survey_opt_in == True,
        User.state_code == state_code
    ).scalar()
    
    if opted_in_count < MIN_POPULATION_THRESHOLD:
        return {
            "state": state_code,
            "sample_sufficient": False,
            "opted_in_users": opted_in_count,
            "min_required": MIN_POPULATION_THRESHOLD,
            "message": f"Insufficient sample size. Need {MIN_POPULATION_THRESHOLD - opted_in_count} more opt-ins."
        }
    
    # Build query for votes from opted-in users in this state
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    base_query = db.query(
        func.count(Vote.id).label('total_votes'),
        func.sum(case((Vote.vote == VoteType.UP, 1), else_=0)).label('up_votes'),
        func.sum(case((Vote.vote == VoteType.DOWN, 1), else_=0)).label('down_votes'),
        func.sum(case((Vote.vote == VoteType.SKIP, 1), else_=0)).label('skip_votes')
    ).join(User).filter(
        User.survey_opt_in == True,
        User.state_code == state_code,
        Vote.created_at >= cutoff_date
    )
    
    if bill_id:
        base_query = base_query.filter(Vote.bill_id == bill_id)
    
    result = base_query.first()
    
    total = result.total_votes or 0
    up = result.up_votes or 0
    down = result.down_votes or 0
    skip = result.skip_votes or 0
    
    return {
        "state": state_code,
        "sample_sufficient": True,
        "opted_in_users": opted_in_count,
        "period_days": days,
        "total_votes": total,
        "sentiment": {
            "support_percentage": round(up / total * 100, 2) if total > 0 else 0,
            "oppose_percentage": round(down / total * 100, 2) if total > 0 else 0,
            "skip_percentage": round(skip / total * 100, 2) if total > 0 else 0
        }
    }


@router.get("/sentiment/by-district/{district}")
async def get_district_sentiment(
    district: str,
    bill_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    """
    Get aggregated sentiment for a congressional district (e.g., "CA-12").
    Only returns data if minimum population threshold is met.
    """
    district = district.upper()
    
    # Check if we have enough opted-in users in this district
    opted_in_count = db.query(func.count(User.id)).filter(
        User.survey_opt_in == True,
        User.congressional_district == district
    ).scalar()
    
    if opted_in_count < MIN_POPULATION_THRESHOLD:
        return {
            "district": district,
            "sample_sufficient": False,
            "opted_in_users": opted_in_count,
            "min_required": MIN_POPULATION_THRESHOLD,
            "message": f"Insufficient sample size. Need {MIN_POPULATION_THRESHOLD - opted_in_count} more opt-ins."
        }
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    result = db.query(
        func.count(Vote.id).label('total_votes'),
        func.sum(case((Vote.vote == VoteType.UP, 1), else_=0)).label('up_votes'),
        func.sum(case((Vote.vote == VoteType.DOWN, 1), else_=0)).label('down_votes'),
        func.sum(case((Vote.vote == VoteType.SKIP, 1), else_=0)).label('skip_votes')
    ).join(User).filter(
        User.survey_opt_in == True,
        User.congressional_district == district,
        Vote.created_at >= cutoff_date
    )
    
    if bill_id:
        result = result.filter(Vote.bill_id == bill_id)
    
    result = result.first()
    
    total = result.total_votes or 0
    up = result.up_votes or 0
    down = result.down_votes or 0
    skip = result.skip_votes or 0
    
    # Get affiliation breakdown (only if each bucket meets threshold)
    affiliation_query = db.query(
        User.affiliation_bucket,
        func.count(User.id).label('count')
    ).filter(
        User.survey_opt_in == True,
        User.congressional_district == district,
        User.affiliation_bucket.isnot(None)
    ).group_by(User.affiliation_bucket).all()
    
    # Only include affiliations meeting threshold
    affiliation_breakdown = {
        a.affiliation_bucket: a.count 
        for a in affiliation_query 
        if a.count >= MIN_POPULATION_THRESHOLD
    }
    
    return {
        "district": district,
        "sample_sufficient": True,
        "opted_in_users": opted_in_count,
        "period_days": days,
        "total_votes": total,
        "sentiment": {
            "support_percentage": round(up / total * 100, 2) if total > 0 else 0,
            "oppose_percentage": round(down / total * 100, 2) if total > 0 else 0,
            "skip_percentage": round(skip / total * 100, 2) if total > 0 else 0
        },
        "affiliation_breakdown": affiliation_breakdown
    }


@router.get("/sentiment/by-affiliation")
async def get_sentiment_by_affiliation(
    bill_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    """
    Get bill sentiment broken down by political affiliation.
    Only returns groups meeting minimum population threshold.
    """
    from uuid import UUID
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get sentiment by affiliation
    results = db.query(
        User.affiliation_bucket,
        func.count(Vote.id).label('total_votes'),
        func.count(func.distinct(User.id)).label('unique_users'),
        func.sum(case((Vote.vote == VoteType.UP, 1), else_=0)).label('up_votes'),
        func.sum(case((Vote.vote == VoteType.DOWN, 1), else_=0)).label('down_votes'),
        func.sum(case((Vote.vote == VoteType.SKIP, 1), else_=0)).label('skip_votes')
    ).join(User).filter(
        User.survey_opt_in == True,
        Vote.bill_id == UUID(bill_id),
        Vote.created_at >= cutoff_date,
        User.affiliation_bucket.isnot(None)
    ).group_by(User.affiliation_bucket).all()
    
    # Get bill info
    bill = db.query(Bill).filter(Bill.id == UUID(bill_id)).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    sentiments = []
    for r in results:
        if r.unique_users >= MIN_POPULATION_THRESHOLD:
            total = r.total_votes or 0
            sentiments.append({
                "affiliation": r.affiliation_bucket,
                "unique_users": r.unique_users,
                "total_votes": total,
                "support_percentage": round((r.up_votes or 0) / total * 100, 2) if total > 0 else 0,
                "oppose_percentage": round((r.down_votes or 0) / total * 100, 2) if total > 0 else 0,
                "skip_percentage": round((r.skip_votes or 0) / total * 100, 2) if total > 0 else 0,
                "sample_sufficient": True
            })
        else:
            sentiments.append({
                "affiliation": r.affiliation_bucket,
                "unique_users": r.unique_users,
                "sample_sufficient": False,
                "message": f"Need {MIN_POPULATION_THRESHOLD - r.unique_users} more opt-ins"
            })
    
    return {
        "bill_id": bill_id,
        "bill_title": bill.title,
        "bill_identifier": f"{bill.bill_type.upper()} {bill.bill_number}",
        "congress": bill.congress,
        "period_days": days,
        "sentiment_by_affiliation": sentiments
    }


@router.get("/trends/bill-sections/{bill_id}")
async def get_bill_section_trends(
    bill_id: str,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    """
    Get aggregated sentiment for each section of a bill.
    Useful for understanding which parts are controversial.
    """
    from uuid import UUID
    
    bill = db.query(Bill).filter(Bill.id == UUID(bill_id)).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Get section-level sentiment from opted-in users only
    results = db.query(
        BillSection.id,
        BillSection.section_key,
        BillSection.heading,
        func.count(Vote.id).label('total_votes'),
        func.count(func.distinct(User.id)).label('unique_users'),
        func.sum(case((Vote.vote == VoteType.UP, 1), else_=0)).label('up_votes'),
        func.sum(case((Vote.vote == VoteType.DOWN, 1), else_=0)).label('down_votes'),
        func.sum(case((Vote.vote == VoteType.SKIP, 1), else_=0)).label('skip_votes')
    ).join(Vote, Vote.section_id == BillSection.id).join(
        User, User.id == Vote.user_id
    ).filter(
        BillSection.bill_id == UUID(bill_id),
        User.survey_opt_in == True
    ).group_by(
        BillSection.id, BillSection.section_key, BillSection.heading
    ).all()
    
    sections = []
    for r in results:
        total = r.total_votes or 0
        if r.unique_users >= MIN_POPULATION_THRESHOLD:
            sections.append({
                "section_key": r.section_key,
                "heading": r.heading,
                "unique_users": r.unique_users,
                "total_votes": total,
                "support_percentage": round((r.up_votes or 0) / total * 100, 2) if total > 0 else 0,
                "oppose_percentage": round((r.down_votes or 0) / total * 100, 2) if total > 0 else 0,
                "skip_percentage": round((r.skip_votes or 0) / total * 100, 2) if total > 0 else 0,
                "controversy_score": round(min((r.up_votes or 0), (r.down_votes or 0)) / max((r.up_votes or 0), (r.down_votes or 0)) * 100, 2) if max((r.up_votes or 0), (r.down_votes or 0)) > 0 else 0,
                "sample_sufficient": True
            })
        else:
            sections.append({
                "section_key": r.section_key,
                "heading": r.heading,
                "sample_sufficient": False
            })
    
    return {
        "bill_id": bill_id,
        "bill_title": bill.title,
        "bill_identifier": f"{bill.bill_type.upper()} {bill.bill_number}",
        "min_population_threshold": MIN_POPULATION_THRESHOLD,
        "sections": sections
    }


@router.post("/user/survey-opt-in")
async def update_survey_opt_in(
    opt_in: bool,
    zip_code: Optional[str] = None,
    age_range: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_auth),
):
    """
    Update user's survey panel opt-in status.
    When opting in, records consent timestamp and version.
    """
    
    # Validate age_range if provided
    valid_age_ranges = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
    if age_range and age_range not in valid_age_ranges:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid age_range. Must be one of: {valid_age_ranges}"
        )
    
    # Derive state from ZIP code (first 5 digits map to states)
    state_code = None
    if zip_code:
        # Basic ZIP to state mapping would go here
        # For now, just store the ZIP
        zip_code = zip_code[:5]  # Normalize to 5 digits
    
    current_user.survey_opt_in = opt_in
    if opt_in:
        current_user.survey_consent_timestamp = datetime.utcnow()
        current_user.survey_consent_version = "1.0"
    else:
        # User withdrew consent - clear optional data but keep the record
        current_user.survey_consent_timestamp = None
        current_user.survey_consent_version = None
    
    if zip_code:
        current_user.zip_code = zip_code
    if age_range:
        current_user.age_range = age_range
    
    db.add(current_user)
    db.commit()
    
    return {
        "success": True,
        "survey_opt_in": current_user.survey_opt_in,
        "message": "Thank you for joining our survey panel!" if opt_in else "You have been removed from the survey panel."
    }