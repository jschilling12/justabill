from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password, get_current_user_auth
from app.database import get_db
from app.models import User
from app.schemas import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
    UserMeResponse,
    UserMeUpdateRequest,
)

router = APIRouter()


def _compute_affiliation_bucket(raw: str | None) -> str | None:
    if not raw:
        return None
    v = raw.strip().lower()
    if not v:
        return None

    # Bucket rules (neutral, user-provided input; we do not infer beyond these keywords)
    republican_tokens = ["republican", "gop", "conservative", "right"]
    liberal_tokens = ["democrat", "democratic", "liberal", "progressive", "left"]

    if any(t in v for t in republican_tokens):
        return "republican"
    if any(t in v for t in liberal_tokens):
        return "liberal"
    return "other"


@router.post("/register", response_model=AuthTokenResponse)
async def register(
    payload: AuthRegisterRequest,
    db: Session = Depends(get_db),
    session_id: str | None = Header(None, alias="X-Session-ID"),
):
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email")
    if not payload.password or len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # If the user has an anonymous session user, upgrade it.
    user = None
    if session_id:
        user = db.query(User).filter(User.session_id == session_id).first()

    if user:
        user.email = email
        user.password_hash = hash_password(payload.password)
        user.is_anonymous = 0
    else:
        user = User(
            email=email,
            password_hash=hash_password(payload.password),
            is_anonymous=0,
            session_id=None,
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id)
    return AuthTokenResponse(access_token=token)


@router.post("/login", response_model=AuthTokenResponse)
async def login(payload: AuthLoginRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.is_anonymous = 0
    db.add(user)
    db.commit()

    token = create_access_token(user_id=user.id)
    return AuthTokenResponse(access_token=token)


@router.get("/me", response_model=UserMeResponse)
async def me(current_user: User = Depends(get_current_user_auth)):
    return current_user


@router.patch("/me", response_model=UserMeResponse)
async def update_me(
    payload: UserMeUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_auth),
):
    # Allow clearing
    current_user.affiliation_raw = payload.affiliation_raw
    current_user.affiliation_bucket = _compute_affiliation_bucket(payload.affiliation_raw)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return current_user
