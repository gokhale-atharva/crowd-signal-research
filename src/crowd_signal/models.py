"""Small typed contracts shared by collection, research and reporting stages."""

import hashlib
import unicodedata
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

NonNegativeInt = Annotated[int, Field(ge=0)]
Score = Annotated[float, Field(ge=-1, le=1, allow_inf_nan=False)]
PositivePrice = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class Direction(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class Position(StrEnum):
    LONG = "long"
    SHORT = "short"
    NONE = "none"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Timestamped(Contract):
    timestamp: AwareDatetime
    original_timezone: str

    @model_validator(mode="before")
    @classmethod
    def preserve_timezone(cls, data: Any):
        if isinstance(data, dict) and "timestamp" in data and "original_timezone" not in data:
            data = dict(data)
            value = data["timestamp"]
            parsed = (
                datetime.fromisoformat(value.replace("Z", "+00:00"))
                if isinstance(value, str)
                else value
            )
            if isinstance(parsed, datetime) and parsed.tzinfo is not None:
                data["original_timezone"] = str(parsed.tzinfo)
        return data

    @field_validator("timestamp")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class Post(Timestamped):
    ticker: str
    text: str = Field(min_length=1)
    source: str
    url: HttpUrl
    likes: NonNegativeInt | None = None
    reposts: NonNegativeInt | None = None
    views: NonNegativeInt | None = None
    author_followers: NonNegativeInt | None = None
    author_hash: str | None = None
    language: str | None = None
    observed_at: AwareDatetime | None = None
    provenance: Literal["live", "synthetic_fixture"] = "live"

    @property
    def content_hash(self) -> str:
        normalized = " ".join(unicodedata.normalize("NFKC", self.text).casefold().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class NewsItem(Timestamped):
    ticker: str
    title: str
    text: str
    url: HttpUrl
    # Publication time alone does not prove historical availability.
    retrieved_at: AwareDatetime
    language: str | None = None
    provenance: Literal["live", "synthetic_fixture"] = "live"


class Extraction(Contract):
    sentiment: Score
    direction: Direction
    stated_position: Position = Position.NONE
    price_levels_mentioned: list[PositivePrice] = Field(default_factory=list)
    is_spam: bool = False
    language: str
    scorer: str


class PriceLevel(Contract):
    price: PositivePrice
    strength: Annotated[float, Field(ge=0, le=1)]
    methods: list[Literal["swing", "pivot", "round", "crowd"]]


class TickerSignal(Contract):
    ticker: str
    asset_name: str
    as_of: AwareDatetime
    current_price: PositivePrice
    mentions: NonNegativeInt
    sentiment: Score
    direction: Direction
    position: Position
    long_authors: NonNegativeInt = 0
    short_authors: NonNegativeInt = 0
    support_levels: list[PriceLevel] = Field(default_factory=list, max_length=2)
    resistance_levels: list[PriceLevel] = Field(default_factory=list, max_length=2)
    news_sentiment: Score | None = None
    sentiment_momentum: Annotated[float, Field(ge=-2, le=2)] | None = None
    disagreement: Annotated[float, Field(ge=0, le=1)] | None = None
    scorer: str
    bull_bear_ratio: float | None = None
    explicit_authors: NonNegativeInt = 0
    unidentified_position_posts: NonNegativeInt = 0
    source_counts: dict[str, int] = Field(default_factory=dict)
    latest_news: list[dict] = Field(default_factory=list)
    evidence_mode: Literal["live", "synthetic_fixture"] = "live"


class Prediction(Contract):
    exchange: str
    ticker: str
    issued_at: AwareDatetime
    features_available_at: AwareDatetime
    target_open: AwareDatetime
    target_session: date
    current_price: PositivePrice
    predicted_price: PositivePrice
    model_name: str
    model_trained_through: date
    mode: Literal["live", "backtest", "synthetic_fixture"]
    confidence_note: str
    lower_price: PositivePrice | None = None
    upper_price: PositivePrice | None = None

    @model_validator(mode="after")
    def causal_contract(self) -> "Prediction":
        if self.lower_price is not None and self.upper_price is not None:
            if self.lower_price > self.upper_price:
                raise ValueError("Forecast price band must be ordered")
        if self.features_available_at > self.issued_at:
            raise ValueError("Features cannot be available after prediction issuance")
        if self.issued_at >= self.target_open:
            raise ValueError("Prediction must be issued before the target session opens")
        if self.model_trained_through >= self.target_session:
            raise ValueError("Training labels must precede the target session")
        return self
