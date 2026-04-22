"""
security.py — JWT 검증 및 API Key 인증

역할 분리:
  - JWT 발급: 맘아이 메인 서버 (이 서버는 발급하지 않음)
  - JWT 검증: 이 서버 (HS256, 공유 시크릿 방식)
  - API Key:  서버 to 서버 호출용 (POST /reports/generate)

사용법:
  JWT 보호 엔드포인트:
    ser_no: str = Depends(get_current_ser_no)

  API Key 보호 엔드포인트:
    _: None = Depends(verify_api_key)
"""
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt

from app.core.config import settings

_bearer = HTTPBearer(auto_error=True)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_current_ser_no(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> str:
    """
    Authorization: Bearer <token> 헤더에서 JWT를 검증하고 ser_no를 반환한다.

    검증 항목:
      1. HS256 서명 검증 (JWT_SECRET)
      2. 만료 시각 (exp 클레임 자동 검증)
      3. payload에 ser_no 클레임 존재 여부

    반환:
      ser_no 문자열 — 라우터에서 데이터 격리에 사용
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=["HS256"],
        )
        ser_no: str | None = payload.get("ser_no")
        if not ser_no:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰에 ser_no가 없습니다",
            )
        return ser_no
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """
    X-API-Key 헤더를 검증한다. 맘아이 서버 → 리포트 서버 호출 전용.

    앱(클라이언트)은 이 인증 방식을 사용하지 않는다.
    API Key가 없거나 일치하지 않으면 403 반환.
    """
    if not api_key or api_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="유효하지 않은 API Key입니다",
        )
