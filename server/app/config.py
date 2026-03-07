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

    model_config = {"env_file": ".env", "env_prefix": "APP_"}


settings = Settings()
