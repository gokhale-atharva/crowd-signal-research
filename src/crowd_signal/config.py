"""Validated exchange configuration and redacted environment settings."""

from datetime import time
from decimal import Decimal
from importlib.resources import files
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

import yaml
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AssetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str
    asset_name: str
    aliases: list[str] = Field(min_length=2)


class ExchangeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    local_name: str | None = None
    timezone: str
    timezone_label: str | None = None
    currency: str
    market_open: time
    market_close: time
    lunch_break: list[time] | None = None
    calendar: str
    proposed_sources: list[str] = Field(min_length=2)
    tickers: list[AssetConfig] = Field(min_length=5, max_length=5)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        ZoneInfo(value)
        return value

    @model_validator(mode="after")
    def consistent(self) -> "ExchangeConfig":
        if len({asset.ticker for asset in self.tickers}) != len(self.tickers):
            raise ValueError("Ticker symbols must be unique within an exchange")
        if len(set(self.proposed_sources)) < 2:
            raise ValueError("At least two distinct proposed sources are required")
        if self.market_open >= self.market_close:
            raise ValueError("Market open must precede close")
        return self


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    exchanges: dict[str, ExchangeConfig]

    def exchange(self, name: str) -> ExchangeConfig:
        try:
            return self.exchanges[name.upper()]
        except KeyError as exc:
            raise ValueError(
                f"Unknown exchange {name!r}; choose {', '.join(self.exchanges)}"
            ) from exc


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    apify_token: SecretStr | None = None
    exa_api_key: SecretStr | None = None
    llm_api_key: SecretStr | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4.1-mini"
    apify_max_items: Annotated[int, Field(ge=1, le=20)] = 20
    apify_max_total_charge_usd: Annotated[Decimal, Field(gt=0, le=Decimal("0.10"))] = Decimal(
        "0.10"
    )
    apify_timeout_seconds: Annotated[int, Field(ge=10, le=300)] = 120

    @field_validator("apify_token", "exa_api_key", "llm_api_key", mode="before")
    @classmethod
    def blank_key_is_missing(cls, value):
        return None if value == "" else value

    def require(self, key: str) -> str:
        value = getattr(self, key)
        if not value or not value.get_secret_value().strip():
            raise ValueError(
                f"Missing {key.upper()}. Copy .env.example to .env and set it locally."
            )
        return value.get_secret_value()


def load_config(path: Path | None = None) -> ProjectConfig:
    content = (
        path.read_text(encoding="utf-8")
        if path
        else files("crowd_signal").joinpath("config/exchanges.yaml").read_text(encoding="utf-8")
    )
    return ProjectConfig.model_validate(yaml.safe_load(content))
