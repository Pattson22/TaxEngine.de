from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def get_current_user_profile(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_current_user_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/confirm-elster-privacy-notice", response_model=UserRead)
def confirm_elster_privacy_notice(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Records that the user has read the Finanzverwaltung's DSGVO Art.
    12-14 info letter (`/elster-datenschutzhinweis`) -- the confirmation
    § 5 Abs. 1 of the ERiC-Lizenzvereinbarung requires before software use
    (see docs/ELSTER_ERIC_INTEGRATION.md section 8). The timestamp is
    always server-generated, never client-suppliable, same reasoning as
    TaxFiling.withdrawal_consent_at."""
    current_user.elster_privacy_notice_confirmed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)
    return current_user
