from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    vapi_private_key: str = Field("", alias="VAPI_PRIVATE_KEY")
    vapi_public_key: str = Field("", alias="VAPI_PUBLIC_KEY")
    vapi_outreach_team_id: Optional[str] = Field(None, alias="VAPI_OUTREACH_TEAM_ID")
    vapi_booking_team_id: Optional[str] = Field(None, alias="VAPI_BOOKING_TEAM_ID")
    openai_api_key: str = Field("", alias="OPENAI_API_KEY")
    openai_realtime_model: str = Field("gpt-4o-realtime-preview", alias="OPENAI_REALTIME_MODEL")
    twilio_account_sid: Optional[str] = Field(None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(None, alias="TWILIO_AUTH_TOKEN")
    twilio_phone_number: Optional[str] = Field(None, alias="TWILIO_PHONE_NUMBER")
    frontend_origin: str = Field("http://localhost:5173", alias="FRONTEND_ORIGIN")
    backend_port: int = Field(8000, alias="BACKEND_PORT")
    venue_data_path: str = Field("backend/app/data/venues.json", alias="VENUE_DATA_PATH")
    callback_secret: Optional[str] = Field(None, alias="CALLBACK_SECRET")
    database_url: str = Field(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/voicebooking",
        alias="DATABASE_URL",
    )
    database_echo: bool = Field(False, alias="DATABASE_ECHO")
    public_backend_url: str = Field("http://localhost:8000", alias="PUBLIC_BACKEND_URL")
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[3] / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def frontend_origins(self) -> List[str]:
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


@property
def frontend_origins(self) -> List[str]:
    return [origin.strip() for origin in str(self.frontend_origin).split(",") if origin.strip()]
