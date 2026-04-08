from __future__ import annotations

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
from services.mcp_service import _CACHE, augment_llm_payload, get_live_context, load_mcp_settings


class StubConnector:
    def __init__(self, provider_name: str, result: ConnectorFetchResult, configured: bool = True):
        self.provider_name = provider_name
        self._result = result
        self._configured = configured

    def is_configured(self) -> bool:
        return self._configured

    def fetch_context(self, brands: list[str], domain: str) -> ConnectorFetchResult:
        return self._result


def sample_settings(enabled: bool = True) -> MCPSettings:
    finance = MCPServerConfig(
        name="Finance MCP",
        enabled=enabled,
        transport="streamable-http",
        tool_name="finance_tool",
        request_timeout_seconds=5.0,
        url="http://finance.example/mcp",
    )
    news = MCPServerConfig(
        name="News MCP",
        enabled=enabled,
        transport="streamable-http",
        tool_name="news_tool",
        request_timeout_seconds=5.0,
        url="http://news.example/mcp",
    )
    return MCPSettings(
        enabled=enabled,
        request_timeout_seconds=5.0,
        cache_ttl_seconds=60,
        finance=finance,
        news=news,
    )


def setup_function() -> None:
    _CACHE.clear()


def test_load_mcp_settings_parses_optional_connector_values():
    settings = load_mcp_settings(
        {
            "MCP_ENABLED": "true",
            "MCP_REQUEST_TIMEOUT_SECONDS": "12",
            "MCP_CACHE_TTL_SECONDS": "90",
            "FINANCE_MCP_TRANSPORT": "stdio",
            "FINANCE_MCP_COMMAND": "python",
            "FINANCE_MCP_ARGS": "[\"server.py\", \"--stdio\"]",
            "FINANCE_MCP_TOOL": "finance_tool",
            "NEWS_MCP_TRANSPORT": "streamable-http",
            "NEWS_MCP_URL": "https://news.example/mcp",
            "NEWS_MCP_HEADERS": "{\"Authorization\": \"Bearer token\"}",
            "NEWS_MCP_TOOL": "news_tool",
        }
    )

    assert settings.enabled is True
    assert settings.cache_ttl_seconds == 90
    assert settings.finance.transport == "stdio"
    assert settings.finance.args == ("server.py", "--stdio")
    assert settings.news.headers == {"Authorization": "Bearer token"}


def test_load_mcp_settings_raises_for_invalid_headers():
    try:
        load_mcp_settings(
            {
                "MCP_ENABLED": "true",
                "NEWS_MCP_HEADERS": "[]",
            }
        )
    except ValueError as exc:
        assert "headers" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected invalid headers to raise ValueError.")


def test_get_live_context_returns_curated_mode_when_disabled():
    bundle = get_live_context(
        ["Michelin", "Goodyear"],
        "Financials",
        settings=sample_settings(enabled=False),
        now=100.0,
    )

    assert bundle.attribution.mode == "curated"
    assert bundle.attribution.providers == ()
    assert "disabled" in bundle.attribution.warnings[0]


def test_get_live_context_merges_success_and_failure_results():
    finance_result = ConnectorFetchResult(
        provider="Finance MCP",
        finance_updates={
            "Michelin": LiveFinanceContext(
                brand="Michelin",
                summary="Strong margin resilience.",
                source="Finance MCP",
                as_of="2026-04-08T12:00:00Z",
                revenue_usd_bn=31.2,
            )
        },
        fetched_at="2026-04-08T12:00:00Z",
    )
    news_result = ConnectorFetchResult(
        provider="News MCP",
        warnings=("News MCP request failed: timeout",),
    )

    bundle = get_live_context(
        ["Michelin", "Goodyear"],
        "Financials",
        settings=sample_settings(),
        connectors=[
            StubConnector("Finance MCP", finance_result),
            StubConnector("News MCP", news_result),
        ],
        now=200.0,
    )

    assert bundle.attribution.mode == "hybrid"
    assert bundle.attribution.providers == ("Finance MCP",)
    assert "timeout" in bundle.attribution.warnings[0]
    assert bundle.finance_updates["Michelin"].revenue_usd_bn == 31.2
    assert bundle.highlights


def test_get_live_context_surfaces_empty_news_as_warning():
    bundle = get_live_context(
        ["Michelin", "Goodyear"],
        "Sustainability",
        settings=sample_settings(),
        connectors=[
            StubConnector(
                "News MCP",
                ConnectorFetchResult(
                    provider="News MCP",
                    warnings=("News MCP returned no usable news details for Michelin.",),
                ),
            )
        ],
        now=300.0,
    )

    assert bundle.attribution.mode == "curated"
    assert "no usable news details" in bundle.attribution.warnings[0]


def test_augment_llm_payload_includes_live_context_details():
    live_context = LiveContextBundle(
        domain="Financials",
        finance_updates={
            "Michelin": LiveFinanceContext(
                brand="Michelin",
                summary="Demand remains strong in premium segments.",
                source="Finance MCP",
                market_cap_usd_bn=29.4,
            )
        },
        news_by_brand={
            "Michelin": BrandNewsContext(
                brand="Michelin",
                source="News MCP",
                themes=("EV demand",),
                headlines=(
                    NewsHeadline(
                        headline="Michelin expands EV lineup",
                        summary="New EV tire investments announced.",
                        source="News MCP",
                        published_at="2026-04-08T11:00:00Z",
                    ),
                ),
            )
        },
        attribution=SourceAttribution(
            mode="hybrid",
            providers=("Finance MCP", "News MCP"),
            freshness_timestamp="2026-04-08T11:00:00Z",
        ),
        highlights=("Michelin: Demand remains strong.",),
    )

    payload = augment_llm_payload([{"brand": "Michelin"}], live_context)

    assert payload["metrics_payload"] == [{"brand": "Michelin"}]
    assert payload["live_context"]["source_mode"] == "hybrid"
    assert payload["live_context"]["providers"] == ["Finance MCP", "News MCP"]
    assert payload["live_context"]["finance_updates"][0]["brand"] == "Michelin"
    assert payload["live_context"]["news_updates"][0]["themes"] == ["EV demand"]
