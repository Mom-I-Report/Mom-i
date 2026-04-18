from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "M-Take 리포트 서버"
    GEMINI_API_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./m_take.db"

    # ETF 시장 데이터 API (없으면 더미 가격 사용)
    MARKET_API_URL: str = ""
    MARKET_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
