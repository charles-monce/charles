"""Configuration for Charles API."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    # AWS Bedrock
    aws_region: str = "eu-west-3"
    aws_bearer_token: Optional[str] = None
    bedrock_model: str = "anthropic.claude-3-haiku-20240307-v1:0"

    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    # Notification limits
    max_notifications_per_day: int = 3

    # Data paths (server-side)
    data_dir: str = "/opt/charles/data"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            aws_region=os.getenv("AWS_REGION", "eu-west-3"),
            aws_bearer_token=os.getenv("AWS_BEARER_TOKEN_BEDROCK"),
            bedrock_model=os.getenv("BEDROCK_MODEL", "anthropic.claude-3-haiku-20240307-v1:0"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            max_notifications_per_day=int(os.getenv("MAX_NOTIFICATIONS_PER_DAY", "3")),
            data_dir=os.getenv("CHARLES_DATA_DIR", "/opt/charles/data"),
            api_host=os.getenv("API_HOST", "0.0.0.0"),
            api_port=int(os.getenv("API_PORT", "8000")),
        )


config = Config.from_env()
