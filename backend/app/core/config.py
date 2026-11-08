from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    spacetimedb_uri: str = "https://maincloud.spacetimedb.com"
    spacetimedb_database: str = ""
    spacetimedb_token: str = ""
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    gemini_model: str = "gemini-3.8-flash"
    gemini_actions_enabled: bool = False
    gemini_timeout_seconds: float = 60.0
    esp32_device_token: str = ""
    pico_device_token: str = ""
    # The standalone SENTINEL Pico 2 W node: reads sensors and drives its own fan,
    # LEDs and buzzer, and reports over USB serial via scripts/serial_bridge.py.
    sentinel_device_id: str = "SENTINEL-01"
    sentinel_device_token: str = ""
    operator_api_key: str = ""
    simulation_enabled: bool = True
    high_temp_threshold: float = 35.0
    critical_temp_threshold: float = 40.0
    recovery_temp_threshold: float = 32.0
    high_humidity_threshold: float = 70.0
    vibration_threshold: float = 0.7
    device_timeout_seconds: int = 15
    telemetry_persist_interval_seconds: int = 5
    recovery_stability_seconds: int = 10
    command_ttl_seconds: int = 30
    telemetry_history_limit: int = 500
    anomaly_model_path: str = str(Path(__file__).resolve().parents[2] / "data" / "models" / "isolation_forest.joblib")
    anomaly_baseline_path: str = str(Path(__file__).resolve().parents[2] / "data" / "baseline" / "baseline.csv")
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
