from pathlib import Path
from pydantic_settings import BaseSettings

# config.py 기준 3단계 상위 = 프로젝트 루트 디렉토리
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "맘아이 리포트 서버"
    GEMINI_API_KEY: str = ""
    DATABASE_URL: str = ""

    # 맘아이 메인 서버가 발급한 JWT를 검증하는 공유 시크릿 (HS256)
    JWT_SECRET: str = ""

    # 맘아이 서버 → 리포트 서버 호출 시 사용하는 API Key (X-API-Key 헤더)
    ADMIN_API_KEY: str = ""

    # 이메일 발송 (Gmail SMTP)
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USER: str = ""
    EMAIL_PASSWORD: str = ""

    # SMS 발송 (Coolsms/Solapi)
    COOLSMS_API_KEY: str = ""
    COOLSMS_API_SECRET: str = ""
    COOLSMS_SENDER: str = ""

    # 프론트엔드 배포 URL (Playwright PDF 캡처용)
    FRONTEND_URL: str = ""

    class Config:
        env_file = str(_ROOT_ENV)
        extra = "ignore"


settings = Settings()
