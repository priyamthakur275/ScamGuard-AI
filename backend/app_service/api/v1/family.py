"""Family Guardian mode endpoints."""
import uuid

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app_service.api.deps import get_current_user
from app_service.core.rate_limit import limiter
from app_service.db.session import get_db
from app_service.services import family

router = APIRouter(prefix="/family", tags=["family"])


class InviteIn(BaseModel):
    email: str = Field(min_length=5, max_length=255)


@router.post("/guardians", status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
def invite_guardian(request: Request, payload: InviteIn, db: Session = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return family.invite(db, user, payload.email)


@router.get("/guardians")
def list_guardians(db: Session = Depends(get_db), user=Depends(get_current_user)) -> list[dict]:
    return family.my_guardians(db, user)


@router.get("/protecting")
def list_protecting(db: Session = Depends(get_db), user=Depends(get_current_user)) -> list[dict]:
    return family.people_i_protect(db, user)


@router.post("/links/{link_id}/accept")
def accept(link_id: uuid.UUID, db: Session = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return family.respond(db, user, link_id, True)


@router.post("/links/{link_id}/decline")
def decline(link_id: uuid.UUID, db: Session = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return family.respond(db, user, link_id, False)


@router.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_link(link_id: uuid.UUID, db: Session = Depends(get_db), user=Depends(get_current_user)) -> None:
    family.remove(db, user, link_id)


@router.get("/alerts")
def list_alerts(db: Session = Depends(get_db), user=Depends(get_current_user)) -> list[dict]:
    return family.alerts(db, user)


@router.get("/summary")
def get_summary(db: Session = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return family.summary(db, user)
