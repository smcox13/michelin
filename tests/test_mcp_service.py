from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

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
from services import mcp_service
from services.mcp_service import (
    _CACHE,
    BRAND_TICKERS,
    FinanceMCPConnector,
    NewsMCPConnector,
    augment_llm_payload,
    get_live_context,
    load_mcp_settings,
)


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


def test_load_mcp_settings_loads_dotenv_with_override_when_using_process_env(monkeypatch):
    called: dict[str, object] = {}

    def fake_load_dotenv(*, override: bool = False):
        called["override"] = override
        monkeypatch.setenv("MCP_ENABLED", "true")
        monkeypatch.setenv("FINANCE_MCP_URL", "https://secedgar.caseyjhand.com/mcp")
        monkeypatch.setenv("FINANCE_MCP_TOOL", "secedgar_get_financials")

    monkeypatch.setattr(mcp_service, "load_dotenv", fake_load_dotenv)

    settings = load_mcp_settings()

    assert called == {"override": True}
    assert settings.enabled is True
    assert settings.finance.url == "https://secedgar.caseyjhand.com/mcp"
    assert settings.finance.tool_name == "secedgar_get_financials"


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


def test_finance_connector_maps_known_brand_to_ticker_for_financial_datasets():
    connector = FinanceMCPConnector(
        MCPServerConfig(
            name="Finance MCP",
            enabled=True,
            transport="streamable-http",
            tool_name="getFinancialMetricsSnapshot",
            request_timeout_seconds=5.0,
            url="https://mcp.financialdatasets.ai/api",
        )
    )

    assert connector._build_arguments("Michelin", "Financials") == {
        "ticker": BRAND_TICKERS["Michelin"]
    }


def test_news_connector_maps_known_brand_to_ticker_for_financial_datasets():
    connector = NewsMCPConnector(
        MCPServerConfig(
            name="News MCP",
            enabled=True,
            transport="streamable-http",
            tool_name="getNews",
            request_timeout_seconds=5.0,
            url="https://mcp.financialdatasets.ai/api",
        )
    )

    assert connector._build_arguments("Bridgestone", "Financials") == {
        "ticker": BRAND_TICKERS["Bridgestone"],
        "limit": 5,
    }


def test_finance_connector_maps_known_brand_to_ticker_for_secedgar():
    connector = FinanceMCPConnector(
        MCPServerConfig(
            name="Finance MCP",
            enabled=True,
            transport="streamable-http",
            tool_name="secedgar_get_financials",
            request_timeout_seconds=5.0,
            url="https://secedgar.caseyjhand.com/mcp",
        )
    )

    assert connector._build_arguments("Goodyear", "Financials") == {
        "ticker": BRAND_TICKERS["Goodyear"]
    }


def test_news_connector_uses_query_for_nhtsa_search():
    connector = NewsMCPConnector(
        MCPServerConfig(
            name="News MCP",
            enabled=True,
            transport="streamable-http",
            tool_name="nhtsa_search_recalls",
            request_timeout_seconds=5.0,
            url="https://nhtsa.caseyjhand.com/mcp",
        )
    )

    assert connector._build_arguments("Michelin", "Products") == {"query": "Michelin"}


def test_augment_llm_payload_supports_text_only_secondary_context():
    live_context = LiveContextBundle(
        domain="Products",
        news_by_brand={
            "Michelin": BrandNewsContext(
                brand="Michelin",
                source="NHTSA MCP",
                headlines=(
                    NewsHeadline(
                        headline="Michelin live context",
                        summary="Recall monitoring context available.",
                        source="NHTSA MCP",
                    ),
                ),
            )
        },
        attribution=SourceAttribution(mode="hybrid", providers=("NHTSA MCP",)),
        highlights=("Michelin: Recall monitoring context available.",),
    )

    payload = augment_llm_payload([{"brand": "Michelin"}], live_context)

    assert payload["live_context"]["news_updates"][0]["headlines"][0]["summary"] == (
        "Recall monitoring context available."
    )


def test_news_connector_uses_empty_args_for_shared_apify_top_news():
    connector = NewsMCPConnector(
        MCPServerConfig(
            name="News MCP",
            enabled=True,
            transport="streamable-http",
            tool_name="get_top_news",
            request_timeout_seconds=5.0,
            url="https://mrbridge--latest-news-mcp-server.apify.actor/mcp?token=test",
        )
    )

    assert connector._build_arguments("Michelin", "Financials") == {}


def test_client_streams_uses_legacy_streamable_http_signature(monkeypatch):
    captured: dict[str, object] = {}

    @asynccontextmanager
    async def legacy_streamable_client(url, headers=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        yield ("read", "write", "session-id")

    def fake_import_module(name: str):
        if name == "mcp":
            return SimpleNamespace()
        if name == "mcp.client.streamable_http":
            return SimpleNamespace(streamablehttp_client=legacy_streamable_client)
        raise AssertionError(f"Unexpected import: {name}")

    monkeypatch.setattr(mcp_service, "import_module", fake_import_module)

    config = MCPServerConfig(
        name="News MCP",
        enabled=True,
        transport="streamable-http",
        tool_name="get_top_news",
        request_timeout_seconds=7.0,
        url="https://example.com/mcp",
        headers={"Authorization": "Bearer token"},
    )

    async def run():
        async with mcp_service._client_streams(config) as streams:
            return streams

    streams = asyncio.run(run())

    assert streams == ("read", "write")
    assert captured == {
        "url": "https://example.com/mcp",
        "headers": {"Authorization": "Bearer token"},
        "timeout": 7.0,
    }


def test_client_streams_builds_http_client_for_modern_streamable_http(monkeypatch):
    captured: dict[str, object] = {}

    class DummyClient:
        async def __aenter__(self):
            captured["client_entered"] = True
            return self

        async def __aexit__(self, exc_type, exc, tb):
            captured["client_exited"] = True
            return False

    def create_mcp_http_client(headers=None, timeout=None):
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyClient()

    @asynccontextmanager
    async def modern_streamable_client(url, *, http_client=None, terminate_on_close=True):
        captured["url"] = url
        captured["http_client"] = http_client
        captured["terminate_on_close"] = terminate_on_close
        yield ("read", "write", "session-id")

    def fake_import_module(name: str):
        if name == "mcp":
            return SimpleNamespace()
        if name == "mcp.client.streamable_http":
            return SimpleNamespace(
                streamable_http_client=modern_streamable_client,
                create_mcp_http_client=create_mcp_http_client,
            )
        raise AssertionError(f"Unexpected import: {name}")

    monkeypatch.setattr(mcp_service, "import_module", fake_import_module)

    config = MCPServerConfig(
        name="Finance MCP",
        enabled=True,
        transport="streamable-http",
        tool_name="secedgar_get_financials",
        request_timeout_seconds=9.0,
        url="https://example.com/mcp",
        headers={"X-Test": "1"},
    )

    async def run():
        async with mcp_service._client_streams(config) as streams:
            return streams

    streams = asyncio.run(run())

    assert streams == ("read", "write")
    assert captured["url"] == "https://example.com/mcp"
    assert captured["headers"] == {"X-Test": "1"}
    assert captured["http_client"].__class__.__name__ == "DummyClient"
    assert captured["client_entered"] is True
    assert captured["client_exited"] is True
