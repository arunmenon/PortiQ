from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://portiq:changeme@localhost:5432/portiq"
    database_url_sync: str = "postgresql://portiq:changeme@localhost:5432/portiq"

    # Application
    environment: str = "development"
    port: int = 8000
    log_level: str = "info"

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # Auth (JWT)
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    portiq_max_tokens: int = 4096
    portiq_max_tool_calls: int = 5

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # AIS — VesselFinder
    vessel_finder_api_key: str = ""
    vessel_finder_base_url: str = "https://api.vesselfinder.com"

    # AIS — PCS1x
    pcs1x_client_id: str = ""
    pcs1x_client_secret: str = ""
    pcs1x_base_url: str = "https://api.pcs1x.gov.in"

    # Polling intervals (seconds)
    vessel_position_poll_seconds: int = 120
    vessel_eta_poll_seconds: int = 300
    vessel_arrival_poll_seconds: int = 900

    # Quality thresholds
    vessel_max_position_age_seconds: int = 3600
    vessel_max_speed_knots: float = 50.0
    vessel_min_signal_confidence: float = 0.7

    # Event outbox
    event_outbox_poll_seconds: int = 5
    event_outbox_batch_size: int = 50

    # Cache TTLs (Redis, seconds)
    vessel_position_cache_ttl: int = 300
    vessel_eta_cache_ttl: int = 900

    # RFQ & Bidding
    rfq_auto_close_poll_seconds: int = 60
    rfq_draft_ttl_days: int = 30

    # Intelligence
    intelligence_mv_refresh_hour: int = 2
    intelligence_supplier_score_refresh_hour: int = 2
    intelligence_price_benchmark_days: int = 90
    intelligence_min_quotes_for_benchmark: int = 3

    # Document AI
    azure_di_endpoint: str = ""
    azure_di_api_key: str = ""
    azure_di_model_layout: str = "prebuilt-layout"
    azure_di_model_read: str = "prebuilt-read"
    extraction_auto_threshold: float = 0.95
    extraction_quick_review_threshold: float = 0.80
    extraction_batch_size: int = 20

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
