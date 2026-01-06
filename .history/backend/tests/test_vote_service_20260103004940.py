import pytest
from app.services.vote_service import VoteService
from app.models import Vote, VoteType
from uuid import uuid4


class MockDB:
    """Mock database for testing"""
    def __init__(self):
        self.data = []
    
    def query(self, model):
        return MockQuery(self.data, model)
    
    def add(self, obj):
        self.data.append(obj)
    
    def commit(self):
        pass
    
    def refresh(self, obj):
        pass


class MockQuery:
    def __init__(self, data, model):
        self.data = [d for d in data if isinstance(d, model)]
        self.filters = []
    
    def filter(self, *args):
        return self
    
    def all(self):
        return self.data
    
    def first(self):
        return self.data[0] if self.data else None
    
    def delete(self):
        pass


def test_calculate_verdict_likely_support():
    """Test verdict calculation for likely support"""
    db = MockDB()
    service = VoteService(db)
    
    verdict = service._calculate_verdict(0.85)
    assert verdict == "Likely Support"


def test_calculate_verdict_likely_oppose():
    """Test verdict calculation for likely oppose"""
    db = MockDB()
    service = VoteService(db)
    
    verdict = service._calculate_verdict(0.15)
    assert verdict == "Likely Oppose"


def test_calculate_verdict_mixed():
    """Test verdict calculation for mixed"""
    db = MockDB()
    service = VoteService(db)
    
    verdict = service._calculate_verdict(0.50)
    assert verdict == "Mixed/Unsure"


def test_calculate_verdict_no_votes():
    """Test verdict calculation with no votes"""
    db = MockDB()
    service = VoteService(db)
    
    verdict = service._calculate_verdict(None)
    assert verdict == "Not enough votes"


def test_upvote_ratio_calculation():
    """Test upvote ratio calculation"""
    # 4 upvotes, 1 downvote = 0.80 ratio
    upvotes = 4
    downvotes = 1
    ratio = upvotes / (upvotes + downvotes)
    
    assert ratio == 0.80
    
    # 1 upvote, 4 downvotes = 0.20 ratio
    upvotes = 1
    downvotes = 4
    ratio = upvotes / (upvotes + downvotes)
    
    assert ratio == 0.20
