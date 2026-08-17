from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment configuration, loaded from .env at import.

    Required vars (database_url, agent_tool_secret) raise at startup if missing, so a
    misconfigured deploy fails fast rather than at the first call.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    agent_tool_secret: str = Field(min_length=16)
    elevenlabs_api_key: str | None = None
    elevenlabs_agent_id: str | None = None
    # Public origin ElevenLabs/Twilio reach for webhooks + tools (tunnel or deploy).
    public_base_url: str | None = None
    # Workspace webhook signing secret — verifies inbound ElevenLabs webhooks.
    elevenlabs_webhook_secret: str | None = None
    # Demo caller so a call from your own phone is recognized. PII — .env only.
    demo_caller_phone: str | None = None
    demo_shop_name: str | None = None
    # Sending the final offer. SMS via Twilio (Account SID + Auth Token + a number);
    # email via Gmail SMTP (your address + a Google App Password, base64-encoded in .env).
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_phone_number: str | None = None
    gmail_address: str | None = None
    gmail_app_password: str | None = None  # base64-encoded Google App Password
    default_locale: str = "en"

    @property
    def sqlalchemy_url(self) -> str:
        """A bare `postgresql://` URL gets the psycopg driver SQLAlchemy needs."""
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        return url


settings = Settings()
