from functools import lru_cache
from typing import Optional

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
    frontend_origin: HttpUrl = Field("http://localhost:5173", alias="FRONTEND_ORIGIN")
    backend_port: int = Field(8000, alias="BACKEND_PORT")
    venue_data_path: str = Field("backend/app/data/venues.json", alias="VENUE_DATA_PATH")
    callback_secret: Optional[str] = Field(None, alias="CALLBACK_SECRET")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
