#!/usr/bin/env python3
"""
Quick database initialization script that creates tables directly using SQLAlchemy models.
This bypasses Alembic migration issues.
"""
import sys
sys.path.insert(0, '/app')

from app.database import engine
from app.models import Base

print("Creating all database tables...")
Base.metadata.create_all(bind=engine)
print("✓ Database tables created successfully!")
