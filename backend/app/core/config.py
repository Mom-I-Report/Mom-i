from pathlib import Path
from pydantic import model_validator
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

    class Config:
        env_file = str(_ROOT_ENV)
        extra = "ignore"

    @model_validator(mode="after")
    def check_required_env(self) -> "Settings":
        missing = [
            name for name, val in {
                "GEMINI_API_KEY": self.GEMINI_API_KEY,
                "DATABASE_URL":   self.DATABASE_URL,
                "JWT_SECRET":     self.JWT_SECRET,
                "ADMIN_API_KEY":  self.ADMIN_API_KEY,
            }.items() if not val
        ]
        if missing:
            raise ValueError(f"필수 환경변수가 설정되지 않았습니다: {', '.join(missing)}")
        return self


settings = Settings()
