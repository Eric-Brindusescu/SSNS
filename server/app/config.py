from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_name: str = "upb-nlp/ro-wav2vec2"
    target_sample_rate: int = 16000
    max_audio_duration_seconds: int = 120
    max_audio_file_size_mb: int = 50
    cors_origins: list[str] = ["*"]
    device: str = "cpu"

    # Decoding parameters (LM-boosted only)
    beam_width: int = 100
    alpha: float = 0.5
    beta: float = 1.5
    hotwords: list[str] = ["stare", "starea", "stare", "depunere", "polei", "zăpadă", "milimetri", "treimi", "treime", "dispecer", "dispecerat", "trun", "suprafață"]
    hotword_weight: float = 30.0

    # Weather API keys (optional — can also be provided via request headers)
    avwx_token: str | None = None
    checkwx_api_key: str | None = None

    # LM Studio settings
    lm_studio_base_url: str = "http://localhost:1234/v1"
    lm_studio_model: str = "default"
    lm_studio_temperature: float = 0.3
    lm_studio_max_tokens: int = 2048

    # SMTP settings for email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""  # Use an app-specific password for Gmail
    smtp_from: str = ""

    model_config = {"env_file": ".env", "env_prefix": "APP_"}


settings = Settings()
