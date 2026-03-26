from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "OptimusAI"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"  # development, staging, production

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "postgresql+asyncpg://optimus:optimus@localhost:5432/optimusai"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Encryption (for social tokens)
    encryption_key: str = "CHANGE-ME-IN-PRODUCTION"  # Fernet key

    # Storage (S3/MinIO)
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "optimusai"
    s3_region: str = "us-east-1"
    s3_public_url: str = ""  # Public URL for browser access (e.g., http://localhost:9002)

    # Facebook
    facebook_app_id: str = ""
    facebook_app_secret: str = ""
    facebook_webhook_verify_token: str = "optimus-verify-token"

    # WhatsApp
    whatsapp_webhook_verify_token: str = "optimus-wa-verify"

    # LLM
    ollama_base_url: str = "http://localhost:11434"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    default_llm_provider: str = "ollama"  # ollama, anthropic, openai

    # Embeddings
    embedding_model: str = "BAAI/bge-m3"
    embedding_dimensions: int = 1024

    # Image Generation
    comfyui_base_url: str = "http://localhost:8188"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:4000", "http://localhost:4001"]

    @property
    def async_database_url(self) -> str:
        return self.database_url


settings = Settings()
