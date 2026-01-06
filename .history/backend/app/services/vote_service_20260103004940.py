from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Dict, Any
import logging

from app.models import Vote, VoteType, BillSection, UserBillSummary
from datetime import datetime

logger = logging.getLogger(__name__)


class VoteService:
    """Service for vote aggregation and support score calculation"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_user_bill_summary(self, user_id: UUID, bill_id: UUID) -> UserBillSummary:
        """
        Generate or regenerate a user's bill summary based on their votes
        Returns support score, verdict, and liked/disliked sections
        """
        
        # Get all user votes for this bill
        votes = self.db.query(Vote).filter(
            Vote.user_id == user_id,
            Vote.bill_id == bill_id
        ).all()
        
        if not votes:
            # No votes yet
            summary = UserBillSummary(
                user_id=user_id,
                bill_id=bill_id,
                upvote_count=0,
                downvote_count=0,
                skip_count=0,
                upvote_ratio=None,
                verdict_label="Not enough votes",
                liked_sections=[],
                disliked_sections=[]
            )
            self.db.add(summary)
            self.db.commit()
            self.db.refresh(summary)
            return summary
        
        # Count votes
        upvote_count = sum(1 for v in votes if v.vote == VoteType.UP)
        downvote_count = sum(1 for v in votes if v.vote == VoteType.DOWN)
        skip_count = sum(1 for v in votes if v.vote == VoteType.SKIP)
        
        # Calculate upvote ratio
        total_decisive_votes = upvote_count + downvote_count
        if total_decisive_votes > 0:
            upvote_ratio = upvote_count / total_decisive_votes
        else:
            upvote_ratio = None
        
        # Determine verdict
        verdict_label = self._calculate_verdict(upvote_ratio)
        
        # Get liked sections (upvoted)
        liked_section_ids = [v.section_id for v in votes if v.vote == VoteType.UP]
        liked_sections = self._get_section_summaries(liked_section_ids)
        
        # Get disliked sections (downvoted)
        disliked_section_ids = [v.section_id for v in votes if v.vote == VoteType.DOWN]
        disliked_sections = self._get_section_summaries(disliked_section_ids)
        
        # Check if summary already exists
        existing_summary = self.db.query(UserBillSummary).filter(
            UserBillSummary.user_id == user_id,
            UserBillSummary.bill_id == bill_id
        ).first()
        
        if existing_summary:
            # Update existing
            existing_summary.upvote_count = upvote_count
            existing_summary.downvote_count = downvote_count
            existing_summary.skip_count = skip_count
            existing_summary.upvote_ratio = upvote_ratio
            existing_summary.verdict_label = verdict_label
            existing_summary.liked_sections = liked_sections
            existing_summary.disliked_sections = disliked_sections
            existing_summary.generated_at = datetime.utcnow()
            summary = existing_summary
        else:
            # Create new
            summary = UserBillSummary(
                user_id=user_id,
                bill_id=bill_id,
                upvote_count=upvote_count,
                downvote_count=downvote_count,
                skip_count=skip_count,
                upvote_ratio=upvote_ratio,
                verdict_label=verdict_label,
                liked_sections=liked_sections,
                disliked_sections=disliked_sections
            )
            self.db.add(summary)
        
        self.db.commit()
        self.db.refresh(summary)
        
        logger.info(f"Generated summary for user {user_id}, bill {bill_id}: {verdict_label}")
        return summary
    
    def _calculate_verdict(self, upvote_ratio: float = None) -> str:
        """Calculate verdict label based on upvote ratio"""
        if upvote_ratio is None:
            return "Not enough votes"
        elif upvote_ratio >= 0.80:
            return "Likely Support"
        elif upvote_ratio <= 0.20:
            return "Likely Oppose"
        else:
            return "Mixed/Unsure"
    
    def _get_section_summaries(self, section_ids: List[UUID]) -> List[Dict[str, Any]]:
        """Get section summaries for display in user recap"""
        if not section_ids:
            return []
        
        sections = self.db.query(BillSection).filter(
            BillSection.id.in_(section_ids)
        ).order_by(BillSection.order_index).all()
        
        result = []
        for section in sections:
            section_data = {
                "section_id": str(section.id),
                "section_key": section.section_key,
                "heading": section.heading,
                "order_index": section.order_index
            }
            
            # Include summary if available
            if section.summary_json:
                section_data["summary"] = section.summary_json.get("plain_summary_bullets", [])
                section_data["evidence_quotes"] = section.evidence_quotes or []
            else:
                section_data["summary"] = ["Summary not yet generated"]
                section_data["evidence_quotes"] = []
            
            result.append(section_data)
        
        return result
