from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_name: str = "upb-nlp/ro-wav2vec2"
    target_sample_rate: int = 16000
    max_audio_duration_seconds: int = 120
    max_audio_file_size_mb: int = 50
    cors_origins: list[str] = ["*"]
    device: str = "cpu"

    model_config = {"env_file": ".env", "env_prefix": "APP_"}


settings = Settings()
