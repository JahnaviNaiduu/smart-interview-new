from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_staff
from app.models.notification_log import NotificationLog

router = APIRouter(prefix="/notifications", tags=["notifications"], dependencies=[Depends(require_staff)])


@router.get("")
def list_notifications(
    limit: int = Query(50, le=200),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(NotificationLog)
    if status:
        query = query.filter(NotificationLog.status == status)
    return query.order_by(NotificationLog.created_at.desc()).limit(limit).all()
