from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Supabase ---
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str

    # --- AWS ---
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "ap-south-1"
    S3_MEDIA_BUCKET: str = "picvibez-media"
    CLOUDFRONT_DOMAIN: str = ""
    CLOUDFRONT_KEY_PAIR_ID: str = ""
    CLOUDFRONT_PRIVATE_KEY_PATH: str = ""
    SQS_MEDIA_QUEUE_URL: str = ""
    REKOGNITION_COLLECTION_PREFIX: str = "picvibez_event_"

    # --- Stripe ---
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # --- Gemini ---
    GEMINI_API_KEY: str = ""

    # --- App ---
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000,capacitor://localhost"
    LOG_LEVEL: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
