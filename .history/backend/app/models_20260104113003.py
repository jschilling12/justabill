from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey, Enum, Float, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.database import Base


class VoteType(str, enum.Enum):
    UP = "up"
    DOWN = "down"
    SKIP = "skip"


class BillStatus(str, enum.Enum):
    INTRODUCED = "introduced"
    IN_COMMITTEE = "in_committee"
    PASSED_HOUSE = "passed_house"
    PASSED_SENATE = "passed_senate"
    IN_CONFERENCE = "in_conference"
    PASSED_BOTH = "passed_both"
    VETOED = "vetoed"
    ENACTED = "enacted"


class Bill(Base):
    __tablename__ = "bills"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    congress = Column(Integer, nullable=False, index=True)
    bill_type = Column(String(10), nullable=False)  # hr, s, hjres, sjres, etc.
    bill_number = Column(Integer, nullable=False)
    title = Column(Text)
    introduced_date = Column(DateTime(timezone=True))
    latest_action_date = Column(DateTime(timezone=True), index=True)
    status = Column(Enum(BillStatus), index=True)
    sponsor = Column(JSON)  # {name, party, state}
    source_urls = Column(JSON)  # {congress_gov, govinfo, etc.}
    raw_metadata = Column(JSON)
    # Popularity and impact
    is_popular = Column(Boolean, nullable=False, server_default="false", index=True)
    popularity_score = Column(Integer, nullable=False, server_default="0")
    popularity_updated_at = Column(DateTime(timezone=True), nullable=True)
    # Whether this bill is a primary law-making vehicle (e.g., HR/S vs simple resolutions)
    is_law_impact_candidate = Column(Boolean, nullable=False, server_default="false", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    versions = relationship("BillVersion", back_populates="bill", cascade="all, delete-orphan")
    sections = relationship("BillSection", back_populates="bill", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="bill", cascade="all, delete-orphan")
    user_summaries = relationship("UserBillSummary", back_populates="bill", cascade="all, delete-orphan")
    
    # Unique constraint
    __table_args__ = (
        Index('ix_bill_identifier', 'congress', 'bill_type', 'bill_number', unique=True),
    )


class BillVersion(Base):
    __tablename__ = "bill_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bill_id = Column(UUID(as_uuid=True), ForeignKey("bills.id"), nullable=False, index=True)
    version_label = Column(String(50))  # ih, eh, enr, etc.
    source_url = Column(Text)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    raw_text = Column(Text)  # Optional: store full text
    content_hash = Column(String(64))  # SHA256 hash of content
    
    # Relationships
    bill = relationship("Bill", back_populates="versions")


class BillSection(Base):
    __tablename__ = "bill_sections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bill_id = Column(UUID(as_uuid=True), ForeignKey("bills.id"), nullable=False, index=True)
    section_key = Column(String(100))  # e.g., "SEC. 101", "TITLE I"
    heading = Column(Text)
    order_index = Column(Integer, nullable=False)
    section_text = Column(Text, nullable=False)
    section_text_hash = Column(String(64))
    
    # Hierarchy fields for grouping
    division = Column(String(50), index=True)  # e.g., "DIVISION A", "DIVISION B"
    title = Column(String(50), index=True)     # e.g., "TITLE I", "TITLE II"
    title_heading = Column(Text)                # e.g., "Border Security"
    
    summary_json = Column(JSON)  # {plain_summary_bullets, key_terms, who_it_affects, uncertainties}
    evidence_quotes = Column(JSON)  # ["quote1", "quote2", "quote3"]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    bill = relationship("Bill", back_populates="sections")
    votes = relationship("Vote", back_populates="section", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_bill_section_order', 'bill_id', 'order_index'),
    )


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    is_anonymous = Column(Integer, default=1)  # 1 for anonymous sessions
    session_id = Column(String(255), unique=True, nullable=True, index=True)  # For anonymous users
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    votes = relationship("Vote", back_populates="user", cascade="all, delete-orphan")
    user_summaries = relationship("UserBillSummary", back_populates="user", cascade="all, delete-orphan")


class Vote(Base):
    __tablename__ = "votes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    bill_id = Column(UUID(as_uuid=True), ForeignKey("bills.id"), nullable=False, index=True)
    section_id = Column(UUID(as_uuid=True), ForeignKey("bill_sections.id"), nullable=False, index=True)
    vote = Column(Enum(VoteType), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="votes")
    bill = relationship("Bill", back_populates="votes")
    section = relationship("BillSection", back_populates="votes")
    
    __table_args__ = (
        Index('ix_user_section_vote', 'user_id', 'section_id', unique=True),
    )


class UserBillSummary(Base):
    __tablename__ = "user_bill_summaries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    bill_id = Column(UUID(as_uuid=True), ForeignKey("bills.id"), nullable=False, index=True)
    upvote_count = Column(Integer, default=0)
    downvote_count = Column(Integer, default=0)
    skip_count = Column(Integer, default=0)
    upvote_ratio = Column(Float, nullable=True)  # upvotes / (upvotes + downvotes)
    verdict_label = Column(String(50))  # "Likely Support", "Likely Oppose", "Mixed/Unsure", "Not enough votes"
    liked_sections = Column(JSON)  # [{section_id, heading, summary}]
    disliked_sections = Column(JSON)  # [{section_id, heading, summary}]
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_summaries")
    bill = relationship("Bill", back_populates="user_summaries")
    
    __table_args__ = (
        Index('ix_user_bill_summary', 'user_id', 'bill_id', unique=True),
    )
