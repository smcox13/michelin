"""Typed models for optional MCP-backed live context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


SourceMode = Literal["curated", "live", "hybrid"]


@dataclass(frozen=True)
class MCPServerConfig:
    """Connection settings for a single MCP-backed provider."""

    name: str
    enabled: bool
    transport: str
    tool_name: str
    request_timeout_seconds: float
    url: str | None = None
    command: str | None = None
    args: tuple[str, ...] = ()
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def configured(self) -> bool:
        if not self.enabled or not self.tool_name:
            return False
        if self.transport == "stdio":
            return bool(self.command)
        return bool(self.url)

    def cache_key(self) -> tuple[object, ...]:
        return (
            self.name,
            self.enabled,
            self.transport,
            self.tool_name,
            self.request_timeout_seconds,
            self.url,
            self.command,
            self.args,
            tuple(sorted(self.headers.items())),
        )


@dataclass(frozen=True)
class MCPSettings:
    """Top-level MCP configuration for the application."""

    enabled: bool
    request_timeout_seconds: float
    cache_ttl_seconds: int
    finance: MCPServerConfig
    news: MCPServerConfig

    def cache_key(self) -> tuple[object, ...]:
        return (
            self.enabled,
            self.request_timeout_seconds,
            self.cache_ttl_seconds,
            self.finance.cache_key(),
            self.news.cache_key(),
        )


@dataclass(frozen=True)
class LiveFinanceContext:
    """Normalized live finance context for a single brand."""

    brand: str
    summary: str
    source: str
    as_of: str | None = None
    revenue_usd_bn: float | None = None
    operating_margin_pct: float | None = None
    market_cap_usd_bn: float | None = None


@dataclass(frozen=True)
class NewsHeadline:
    """Normalized live news item for a single brand."""

    headline: str
    summary: str
    source: str
    published_at: str | None = None


@dataclass(frozen=True)
class BrandNewsContext:
    """Normalized news context for a single brand."""

    brand: str
    source: str
    themes: tuple[str, ...] = ()
    headlines: tuple[NewsHeadline, ...] = ()


@dataclass(frozen=True)
class SourceAttribution:
    """Summary of where comparison context came from."""

    mode: SourceMode
    providers: tuple[str, ...] = ()
    freshness_timestamp: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConnectorFetchResult:
    """Connector output before orchestration merge rules are applied."""

    provider: str
    finance_updates: dict[str, LiveFinanceContext] = field(default_factory=dict)
    news_by_brand: dict[str, BrandNewsContext] = field(default_factory=dict)
    fetched_at: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class LiveContextBundle:
    """Merged live context exposed to the UI and LLM service."""

    domain: str
    finance_updates: dict[str, LiveFinanceContext] = field(default_factory=dict)
    news_by_brand: dict[str, BrandNewsContext] = field(default_factory=dict)
    attribution: SourceAttribution = field(
        default_factory=lambda: SourceAttribution(mode="curated")
    )
    highlights: tuple[str, ...] = ()

    def has_live_data(self) -> bool:
        return bool(self.finance_updates or self.news_by_brand)

