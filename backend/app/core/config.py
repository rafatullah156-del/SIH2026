from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str

    # storage: "postgres" (no-card cloud friendly) or "s3"
    STORAGE_BACKEND: str = "postgres"

    # S3/MinIO optional now (only used if STORAGE_BACKEND="s3")
    S3_ENDPOINT: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = ""

    CORS_ORIGINS: str = "*"

    PAIR_TOKEN_TTL_SECONDS: int = 600
    TOKEN_HASH_SALT: str = "change-me-in-prod"

    # optional; we will auto-build joinUrl from request Origin
    FRONTEND_QUICK_UPLOAD_BASE_URL: str = ""

    # keep OFF by default so calibration not required on cloud deploy
    FONT_CHECK_ENABLED: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
