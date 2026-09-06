from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str

    S3_ENDPOINT: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET: str

    CORS_ORIGINS: str = "*"

    PAIR_TOKEN_TTL_SECONDS: int = 600
    TOKEN_HASH_SALT: str = "change-me-in-prod"

    FRONTEND_QUICK_UPLOAD_BASE_URL: str = "http://localhost:8081/quick-upload"
    FONT_CHECK_ENABLED: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()