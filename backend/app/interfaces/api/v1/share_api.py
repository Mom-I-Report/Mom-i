"""
share_api.py — 알림 수신자(공유 목록) API 라우터

엔드포인트:
  POST   /api/v1/share-targets         — 수신자 추가 (JWT)
  GET    /api/v1/share-targets         — 수신자 목록 조회 (JWT)
  DELETE /api/v1/share-targets/{id}    — 수신자 삭제 (JWT)

제약:
  - 디바이스당 최대 5명
  - 동일 연락처 중복 등록 불가 (DB UNIQUE)
  - 본인 디바이스(ser_no) 수신자만 접근 가능
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.infrastructure.database.session import get_db
from app.core.security import get_current_ser_no
from app.domain.share.schemas import ShareTargetCreate, ShareTargetResponse, ShareTargetListResponse
from app.infrastructure.database.repository import share_repo

router = APIRouter()


@router.post(
    "",
    response_model=ShareTargetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="알림 수신자 추가",
)
def add_share_target(
    body: ShareTargetCreate,
    db: Session = Depends(get_db),
    ser_no: str = Depends(get_current_ser_no),
):
    """
    SMS 또는 이메일 알림을 받을 수신자를 등록합니다.
    디바이스당 최대 5명까지 등록 가능합니다.
    """
    if share_repo.count_targets(db, ser_no) >= share_repo.MAX_TARGETS_PER_DEVICE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"수신자는 최대 {share_repo.MAX_TARGETS_PER_DEVICE}명까지 등록할 수 있습니다",
        )
    try:
        return share_repo.create_target(db, ser_no, body.name, body.contact, body.type)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 연락처입니다",
        )


@router.get(
    "",
    response_model=ShareTargetListResponse,
    summary="알림 수신자 목록 조회",
)
def list_share_targets(
    db: Session = Depends(get_db),
    ser_no: str = Depends(get_current_ser_no),
):
    targets = share_repo.get_targets(db, ser_no)
    return ShareTargetListResponse(targets=targets, total=len(targets))


@router.delete(
    "/{target_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="알림 수신자 삭제",
)
def delete_share_target(
    target_id: int,
    db: Session = Depends(get_db),
    ser_no: str = Depends(get_current_ser_no),
):
    target = share_repo.get_target_by_id(db, target_id)
    if not target or target.ser_no != ser_no:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="수신자를 찾을 수 없습니다")
    share_repo.delete_target(db, target)
