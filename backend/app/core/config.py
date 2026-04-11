from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "M-Take Sleep Analysis"
    GEMINI_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
