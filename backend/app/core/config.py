from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "M-Take Sleep Analysis"
    GEMINI_API_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./m_take.db"

    class Config:
        env_file = ".env"


settings = Settings()
