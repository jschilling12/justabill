from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from app.models import VoteType, BillStatus


# Bill Schemas
class BillBase(BaseModel):
    congress: int
    bill_type: str
    bill_number: int
    title: Optional[str] = None
    introduced_date: Optional[datetime] = None
    latest_action_date: Optional[datetime] = None
    status: Optional[BillStatus] = None
    sponsor: Optional[Dict[str, Any]] = None
    source_urls: Optional[Dict[str, Any]] = None


class BillCreate(BillBase):
    raw_metadata: Optional[Dict[str, Any]] = None


class BillResponse(BillBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    is_popular: bool = False
    popularity_score: int = 0
    popularity_updated_at: Optional[datetime] = None
    is_law_impact_candidate: bool = False
    
    class Config:
        from_attributes = True


class BillWithSections(BillResponse):
    sections: List["SectionResponse"] = []


# Section Schemas
class SectionBase(BaseModel):
    section_key: Optional[str] = None
    heading: Optional[str] = None
    division: Optional[str] = None
    title: Optional[str] = None
    title_heading: Optional[str] = None
    order_index: int
    section_text: str


class SectionCreate(SectionBase):
    bill_id: UUID


class SectionResponse(SectionBase):
    id: UUID
    bill_id: UUID
    section_text_hash: Optional[str] = None
    summary_json: Optional[Dict[str, Any]] = None
    evidence_quotes: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Vote Schemas
class VoteCreate(BaseModel):
    section_id: UUID
    vote: VoteType


class VoteResponse(BaseModel):
    id: UUID
    user_id: UUID
    bill_id: UUID
    section_id: UUID
    vote: VoteType
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class VoteSubmitResponse(BaseModel):
    vote: VoteResponse
    updated: bool


class VoteCounts(BaseModel):
    up: int = 0
    down: int = 0
    skip: int = 0
    total: int = 0


class VotePercents(BaseModel):
    agree_pct: float = 0.0
    disagree_pct: float = 0.0


class VoteStatsResponse(BaseModel):
    counts: VoteCounts
    percents: VotePercents


class SegmentStats(BaseModel):
    bucket: str  # republican | liberal | other
    counts: VoteCounts
    percents: VotePercents


class VoteStatsWithSegmentsResponse(VoteStatsResponse):
    segments: List[SegmentStats] = []


class AuthRegisterRequest(BaseModel):
    email: str
    password: str


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserMeResponse(BaseModel):
    id: UUID
    email: Optional[str] = None
    affiliation_raw: Optional[str] = None
    affiliation_bucket: Optional[str] = None

    class Config:
        from_attributes = True


class UserMeUpdateRequest(BaseModel):
    affiliation_raw: Optional[str] = None


# User Summary Schemas
class UserBillSummaryResponse(BaseModel):
    id: UUID
    user_id: UUID
    bill_id: UUID
    upvote_count: int
    downvote_count: int
    skip_count: int
    upvote_ratio: Optional[float]
    verdict_label: str
    liked_sections: List[Dict[str, Any]]
    disliked_sections: List[Dict[str, Any]]
    generated_at: datetime
    
    class Config:
        from_attributes = True


# Ingestion Schemas
class IngestBillRequest(BaseModel):
    congress: int
    bill_type: str
    bill_number: int
    metadata: Optional[Dict[str, Any]] = None


class IngestBillResponse(BaseModel):
    bill_id: UUID
    status: str
    message: str
    sections_created: int


# LLM Schemas
class SummarySectionInput(BaseModel):
    section_key: Optional[str]
    heading: Optional[str]
    section_text: str


class SummarySectionOutput(BaseModel):
    plain_summary_bullets: List[str] = Field(description="5-10 bullet point summary")
    key_terms: Optional[List[str]] = Field(default=None, description="Important terms defined")
    who_it_affects: Optional[List[str]] = Field(default=None, description="Who this section affects")
    evidence_quotes: List[str] = Field(description="1-3 short quotes from section text as evidence")
    uncertainties: Optional[List[str]] = Field(default=None, description="Anything unclear or missing")


# Health Check
class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database: str
    redis: str
    version: str = "1.0.0"


# Pagination
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedBillsResponse(BaseModel):
    items: List[BillResponse]
    total: int
    page: int
    page_size: int
    pages: int


class BillPopularityUpdate(BaseModel):
    is_popular: Optional[bool] = None
    popularity_score: Optional[int] = None


# Update forward refs
BillWithSections.model_rebuild()
