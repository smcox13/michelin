"""Optional MCP-backed live data orchestration for TireLens."""

from __future__ import annotations

import asyncio
import json
import os
import shlex
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from importlib import import_module
from typing import Any, Iterator

from services.mcp_models import (
    BrandNewsContext,
    ConnectorFetchResult,
    LiveContextBundle,
    LiveFinanceContext,
    MCPServerConfig,
    MCPSettings,
    NewsHeadline,
    SourceAttribution,
)

BRAND_TICKERS = {
    "Michelin": "MGDDY",
    "Goodyear": "GT",
    "Continental": "CTTAY",
    "Bridgestone": "BRDCY",
}


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_float(value: str | None, default: float) -> float:
    if value is None or not value.strip():
        return default
    return float(value)


def _parse_int(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    return int(value)


def _parse_args(value: str | None) -> tuple[str, ...]:
    if value is None or not value.strip():
        return ()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return tuple(shlex.split(value))
    if isinstance(parsed, list):
        return tuple(str(item) for item in parsed)
    raise ValueError("MCP args must be a JSON list or shell-style string.")


def _parse_headers(value: str | None) -> dict[str, str]:
    if value is None or not value.strip():
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("MCP headers must be a JSON object.")
    return {str(key): str(header_value) for key, header_value in parsed.items()}


def _build_server_config(
    prefix: str,
    name: str,
    env: dict[str, str],
    request_timeout_seconds: float,
) -> MCPServerConfig:
    transport = env.get(f"{prefix}_TRANSPORT", "streamable-http").strip().lower()
    if transport not in {"stdio", "sse", "streamable-http"}:
        raise ValueError(f"Unsupported MCP transport for {prefix}: {transport}")

    return MCPServerConfig(
        name=name,
        enabled=_parse_bool(env.get(f"{prefix}_ENABLED"), True),
        transport=transport,
        tool_name=env.get(f"{prefix}_TOOL", "").strip(),
        request_timeout_seconds=_parse_float(
            env.get(f"{prefix}_REQUEST_TIMEOUT_SECONDS"),
            request_timeout_seconds,
        ),
        url=env.get(f"{prefix}_URL"),
        command=env.get(f"{prefix}_COMMAND"),
        args=_parse_args(env.get(f"{prefix}_ARGS")),
        headers=_parse_headers(env.get(f"{prefix}_HEADERS")),
    )


def load_mcp_settings(env: dict[str, str] | None = None) -> MCPSettings:
    """Load MCP configuration from environment variables."""

    merged_env = dict(os.environ if env is None else env)
    enabled = _parse_bool(merged_env.get("MCP_ENABLED"), False)
    request_timeout_seconds = _parse_float(
        merged_env.get("MCP_REQUEST_TIMEOUT_SECONDS"),
        8.0,
    )
    cache_ttl_seconds = _parse_int(merged_env.get("MCP_CACHE_TTL_SECONDS"), 300)

    return MCPSettings(
        enabled=enabled,
        request_timeout_seconds=request_timeout_seconds,
        cache_ttl_seconds=cache_ttl_seconds,
        finance=_build_server_config(
            "FINANCE_MCP",
            "Finance MCP",
            merged_env,
            request_timeout_seconds,
        ),
        news=_build_server_config(
            "NEWS_MCP",
            "News MCP",
            merged_env,
            request_timeout_seconds,
        ),
    )


def _iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _brand_symbol(brand: str) -> str:
    return BRAND_TICKERS.get(brand, brand)


def _extract_text_content(result: Any) -> str:
    content = getattr(result, "content", None) or []
    for block in content:
        text = getattr(block, "text", None)
        if text:
            return str(text)
    return ""


def _extract_structured_result(result: Any) -> Any:
    for attribute in ("structuredContent", "structured_content"):
        structured = getattr(result, attribute, None)
        if structured not in (None, {}):
            return structured

    text = _extract_text_content(result)
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"text": text}


@asynccontextmanager
async def _client_streams(config: MCPServerConfig) -> Iterator[tuple[Any, Any]]:
    mcp_module = import_module("mcp")
    if config.transport == "stdio":
        stdio_client = getattr(import_module("mcp.client.stdio"), "stdio_client")
        server_params = getattr(mcp_module, "StdioServerParameters")(
            command=config.command,
            args=list(config.args),
            env=os.environ.copy(),
        )
        async with stdio_client(server_params) as streams:
            yield streams
        return

    if config.transport == "sse":
        sse_client = getattr(import_module("mcp.client.sse"), "sse_client")
        async with sse_client(config.url, headers=config.headers or None) as streams:
            yield streams
        return

    streamable_http_client = getattr(
        import_module("mcp.client.streamable_http"),
        "streamable_http_client",
    )
    async with streamable_http_client(
        config.url,
        headers=config.headers or None,
    ) as streams:
        yield streams[:2]


class MCPConnector(ABC):
    """Small connector interface for MCP-backed data sources."""

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config

    @property
    def provider_name(self) -> str:
        return self.config.name

    def is_configured(self) -> bool:
        return self.config.configured

    def metadata(self) -> dict[str, Any]:
        target = self.config.url or self.config.command or "unconfigured"
        return {
            "provider": self.provider_name,
            "transport": self.config.transport,
            "target": target,
            "tool_name": self.config.tool_name,
            "configured": self.is_configured(),
        }

    def health_check(self) -> tuple[bool, str | None]:
        if not self.is_configured():
            return False, f"{self.provider_name} is not fully configured."

        try:
            asyncio.run(self._list_tools())
        except ModuleNotFoundError:
            return False, "Install the 'mcp' package to enable MCP connectors."
        except Exception as exc:  # pragma: no cover - transport/runtime surface
            return False, f"{self.provider_name} health check failed: {exc}"
        return True, None

    def fetch_context(self, brands: list[str], domain: str) -> ConnectorFetchResult:
        if not self.is_configured():
            return ConnectorFetchResult(
                provider=self.provider_name,
                warnings=(f"{self.provider_name} is not fully configured.",),
            )

        try:
            return asyncio.run(
                asyncio.wait_for(
                    self._fetch_context_async(brands, domain),
                    timeout=self.config.request_timeout_seconds,
                )
            )
        except ModuleNotFoundError:
            return ConnectorFetchResult(
                provider=self.provider_name,
                warnings=("Install the 'mcp' package to enable MCP connectors.",),
            )
        except Exception as exc:  # pragma: no cover - network/runtime surface
            return ConnectorFetchResult(
                provider=self.provider_name,
                warnings=(f"{self.provider_name} request failed: {exc}",),
            )

    async def _list_tools(self) -> list[str]:
        mcp_module = import_module("mcp")
        client_session = getattr(mcp_module, "ClientSession")
        async with _client_streams(self.config) as (read_stream, write_stream):
            async with client_session(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                return [tool.name for tool in getattr(tools, "tools", [])]

    async def _call_tool(self, arguments: dict[str, Any]) -> Any:
        mcp_module = import_module("mcp")
        client_session = getattr(mcp_module, "ClientSession")
        async with _client_streams(self.config) as (read_stream, write_stream):
            async with client_session(read_stream, write_stream) as session:
                await session.initialize()
                return await session.call_tool(self.config.tool_name, arguments=arguments)

    def _build_arguments(self, brand: str, domain: str) -> dict[str, Any]:
        return {"brand": brand, "domain": domain}

    @abstractmethod
    async def _fetch_context_async(
        self,
        brands: list[str],
        domain: str,
    ) -> ConnectorFetchResult:
        """Fetch live context for the selected brands."""


class FinanceMCPConnector(MCPConnector):
    """Example finance adapter that calls a finance-oriented MCP tool."""

    async def _fetch_context_async(
        self,
        brands: list[str],
        domain: str,
    ) -> ConnectorFetchResult:
        finance_updates: dict[str, LiveFinanceContext] = {}
        warnings: list[str] = []
        fetched_at: str | None = None

        for brand in brands:
            raw_result = await self._call_tool(self._build_arguments(brand, domain))
            payload = _extract_structured_result(raw_result)
            if not isinstance(payload, dict):
                warnings.append(f"{self.provider_name} returned an unexpected finance payload.")
                continue

            metrics = payload
            if isinstance(payload.get("metrics"), dict):
                metrics = payload["metrics"]
            elif isinstance(payload.get("snapshot"), dict):
                metrics = payload["snapshot"]
            elif isinstance(payload.get("company_facts"), dict):
                metrics = payload["company_facts"]

            normalized_brand = str(payload.get("brand") or metrics.get("brand") or brand)
            market_cap_usd_bn = _coerce_float(
                metrics.get("market_cap_usd_bn") or metrics.get("market_cap")
            )
            if market_cap_usd_bn is not None and market_cap_usd_bn > 1000:
                market_cap_usd_bn = market_cap_usd_bn / 1_000_000_000

            operating_margin_pct = _coerce_float(
                metrics.get("operating_margin_pct") or metrics.get("operating_margin")
            )
            if operating_margin_pct is not None and 0 <= operating_margin_pct <= 1:
                operating_margin_pct = operating_margin_pct * 100

            summary = str(payload.get("summary") or metrics.get("summary") or "").strip()
            if not summary:
                finance_parts = []
                if market_cap_usd_bn is not None:
                    finance_parts.append(f"market cap {market_cap_usd_bn:.2f}B USD")
                if operating_margin_pct is not None:
                    finance_parts.append(f"operating margin {operating_margin_pct:.1f}%")
                if finance_parts:
                    summary = f"Latest live finance snapshot shows {', '.join(finance_parts)}."

            finance_context = LiveFinanceContext(
                brand=normalized_brand,
                summary=summary,
                source=str(payload.get("source") or self.provider_name),
                as_of=_normalize_timestamp(payload.get("as_of") or metrics.get("as_of")),
                revenue_usd_bn=_coerce_float(metrics.get("revenue_usd_bn")),
                operating_margin_pct=operating_margin_pct,
                market_cap_usd_bn=market_cap_usd_bn,
            )
            if not finance_context.summary and all(
                value is None
                for value in (
                    finance_context.revenue_usd_bn,
                    finance_context.operating_margin_pct,
                    finance_context.market_cap_usd_bn,
                )
            ):
                warnings.append(
                    f"{self.provider_name} returned no usable finance details for {brand}."
                )
                continue

            finance_updates[normalized_brand] = finance_context
            fetched_at = finance_context.as_of or fetched_at or _iso_now()

        return ConnectorFetchResult(
            provider=self.provider_name,
            finance_updates=finance_updates,
            fetched_at=fetched_at,
            warnings=tuple(warnings),
        )

    def _build_arguments(self, brand: str, domain: str) -> dict[str, Any]:
        tool_name = self.config.tool_name
        if tool_name in {"getFinancialMetricsSnapshot", "getCompanyFacts"}:
            return {"ticker": _brand_symbol(brand)}
        return super()._build_arguments(brand, domain)


class NewsMCPConnector(MCPConnector):
    """Example news adapter that calls a recent-news MCP tool."""

    async def _fetch_context_async(
        self,
        brands: list[str],
        domain: str,
    ) -> ConnectorFetchResult:
        news_by_brand: dict[str, BrandNewsContext] = {}
        warnings: list[str] = []
        fetched_at: str | None = None

        for brand in brands:
            raw_result = await self._call_tool(self._build_arguments(brand, domain))
            payload = _extract_structured_result(raw_result)
            if not isinstance(payload, dict):
                warnings.append(f"{self.provider_name} returned an unexpected news payload.")
                continue

            items = payload.get("items", [])
            if not isinstance(items, list) and isinstance(payload.get("news"), list):
                items = payload.get("news", [])
            if not isinstance(items, list):
                warnings.append(f"{self.provider_name} returned malformed news items for {brand}.")
                continue

            headlines: list[NewsHeadline] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                headline = str(item.get("headline") or item.get("title") or "").strip()
                sentiment = str(item.get("sentiment") or "").strip()
                source = str(item.get("source") or payload.get("source") or self.provider_name)
                summary = str(item.get("summary") or headline).strip()
                if not item.get("summary") and sentiment:
                    summary = f"{summary} Sentiment: {sentiment}."
                if not headline and not summary:
                    continue
                headlines.append(
                    NewsHeadline(
                        headline=headline or summary,
                        summary=summary or headline,
                        source=source,
                        published_at=_normalize_timestamp(item.get("published_at") or item.get("date")),
                    )
                )

            themes_raw = payload.get("themes", [])
            if not themes_raw:
                themes_raw = [item.get("sentiment") for item in items if isinstance(item, dict)]
            themes = tuple(str(theme).strip() for theme in themes_raw if str(theme).strip())
            if not headlines and not themes:
                warnings.append(f"{self.provider_name} returned no usable news details for {brand}.")
                continue

            normalized_brand = str(payload.get("brand") or brand)
            news_by_brand[normalized_brand] = BrandNewsContext(
                brand=normalized_brand,
                source=str(payload.get("source") or self.provider_name),
                themes=themes,
                headlines=tuple(headlines),
            )
            latest_item_timestamp = next(
                (headline.published_at for headline in headlines if headline.published_at),
                None,
            )
            fetched_at = latest_item_timestamp or fetched_at or _iso_now()

        return ConnectorFetchResult(
            provider=self.provider_name,
            news_by_brand=news_by_brand,
            fetched_at=fetched_at,
            warnings=tuple(warnings),
        )

    def _build_arguments(self, brand: str, domain: str) -> dict[str, Any]:
        if self.config.tool_name == "getNews":
            return {"ticker": _brand_symbol(brand), "limit": 5}
        return super()._build_arguments(brand, domain)


_CACHE: dict[tuple[object, ...], tuple[float, LiveContextBundle]] = {}


def _build_highlights(bundle: LiveContextBundle) -> tuple[str, ...]:
    highlights: list[str] = []

    for finance in bundle.finance_updates.values():
        numeric_bits = []
        if finance.revenue_usd_bn is not None:
            numeric_bits.append(f"Revenue {finance.revenue_usd_bn:.2f}B USD")
        if finance.operating_margin_pct is not None:
            numeric_bits.append(f"Margin {finance.operating_margin_pct:.1f}%")
        if finance.market_cap_usd_bn is not None:
            numeric_bits.append(f"Market cap {finance.market_cap_usd_bn:.2f}B USD")

        parts = [finance.brand]
        if numeric_bits:
            parts.append(", ".join(numeric_bits))
        if finance.summary:
            parts.append(finance.summary)
        highlights.append(": ".join([parts[0], " | ".join(parts[1:])]))

    for news in bundle.news_by_brand.values():
        if news.themes:
            highlights.append(f"{news.brand}: Themes include {', '.join(news.themes)}.")
        elif news.headlines:
            highlights.append(f"{news.brand}: {news.headlines[0].headline}")

    return tuple(highlights)


def _merge_results(domain: str, results: list[ConnectorFetchResult]) -> LiveContextBundle:
    providers = tuple(
        dict.fromkeys(result.provider for result in results if result.finance_updates or result.news_by_brand)
    )
    warnings = tuple(
        warning
        for result in results
        for warning in result.warnings
    )
    finance_updates: dict[str, LiveFinanceContext] = {}
    news_by_brand: dict[str, BrandNewsContext] = {}
    freshness_candidates = [result.fetched_at for result in results if result.fetched_at]

    for result in results:
        finance_updates.update(result.finance_updates)
        news_by_brand.update(result.news_by_brand)

    mode = "hybrid" if providers else "curated"
    attribution = SourceAttribution(
        mode=mode,
        providers=providers,
        freshness_timestamp=max(freshness_candidates) if freshness_candidates else None,
        warnings=warnings,
    )
    bundle = LiveContextBundle(
        domain=domain,
        finance_updates=finance_updates,
        news_by_brand=news_by_brand,
        attribution=attribution,
    )
    return LiveContextBundle(
        domain=bundle.domain,
        finance_updates=bundle.finance_updates,
        news_by_brand=bundle.news_by_brand,
        attribution=bundle.attribution,
        highlights=_build_highlights(bundle),
    )


def get_live_context(
    brands: list[str],
    domain: str,
    settings: MCPSettings | None = None,
    connectors: list[MCPConnector] | None = None,
    now: float | None = None,
) -> LiveContextBundle:
    """Fetch and cache optional live context from configured MCP servers."""

    resolved_settings = settings or load_mcp_settings()
    current_time = time.time() if now is None else now
    cache_key = (
        tuple(sorted(brands)),
        domain,
        resolved_settings.cache_key(),
    )
    cached_entry = _CACHE.get(cache_key)
    if cached_entry and current_time - cached_entry[0] < resolved_settings.cache_ttl_seconds:
        return cached_entry[1]

    if not resolved_settings.enabled:
        bundle = LiveContextBundle(
            domain=domain,
            attribution=SourceAttribution(
                mode="curated",
                warnings=("MCP enrichment is disabled.",),
            ),
        )
        _CACHE[cache_key] = (current_time, bundle)
        return bundle

    resolved_connectors = connectors or [
        FinanceMCPConnector(resolved_settings.finance),
        NewsMCPConnector(resolved_settings.news),
    ]

    results: list[ConnectorFetchResult] = []
    configured_connectors = [connector for connector in resolved_connectors if connector.is_configured()]
    for connector in resolved_connectors:
        if not connector.is_configured():
            results.append(
                ConnectorFetchResult(
                    provider=connector.provider_name,
                    warnings=(f"{connector.provider_name} is not fully configured.",),
                )
            )

    if configured_connectors:
        with ThreadPoolExecutor(max_workers=len(configured_connectors)) as executor:
            future_map = {
                executor.submit(connector.fetch_context, brands, domain): connector
                for connector in configured_connectors
            }
            for future in as_completed(future_map):
                connector = future_map[future]
                try:
                    results.append(future.result())
                except Exception as exc:  # pragma: no cover - thread/runtime surface
                    results.append(
                        ConnectorFetchResult(
                            provider=connector.provider_name,
                            warnings=(f"{connector.provider_name} request failed: {exc}",),
                        )
                    )
    elif not results:
        results.append(
            ConnectorFetchResult(
                provider="MCP",
                warnings=("MCP is enabled, but no connectors are configured.",),
            )
        )

    bundle = _merge_results(domain, results)
    _CACHE[cache_key] = (current_time, bundle)
    return bundle


def augment_llm_payload(
    base_payload: list[dict[str, Any]],
    live_context: LiveContextBundle,
) -> dict[str, Any]:
    """Package curated and live context into one structured AI input."""

    finance_updates = [
        asdict(finance_context)
        for finance_context in live_context.finance_updates.values()
    ]
    news_updates = [
        {
            "brand": news_context.brand,
            "source": news_context.source,
            "themes": list(news_context.themes),
            "headlines": [asdict(headline) for headline in news_context.headlines],
        }
        for news_context in live_context.news_by_brand.values()
    ]

    return {
        "metrics_payload": base_payload,
        "live_context": {
            "source_mode": live_context.attribution.mode,
            "providers": list(live_context.attribution.providers),
            "freshness_timestamp": live_context.attribution.freshness_timestamp,
            "warnings": list(live_context.attribution.warnings),
            "finance_updates": finance_updates,
            "news_updates": news_updates,
            "highlights": list(live_context.highlights),
        },
    }
