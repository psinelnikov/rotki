import asyncio
from typing import Any

from rotkehlchen.mcp.backend import get_backend_config, request_api
from rotkehlchen.mcp.registry import register_tool


@register_tool(name='get_owned_assets')
async def get_owned_assets() -> dict[str, Any]:
    """Retrieve the list of all assets the user currently owns or has owned."""
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='assets',
        timeout=cfg.timeout,
    )


@register_tool(name='get_asset_mappings')
async def get_asset_mappings(identifiers: list[str]) -> dict[str, Any]:
    """Resolve asset identifiers to their full metadata (name, symbol, type, etc.).

    Essential for translating asset IDs returned by other tools into
    human-readable information.

    Args:
        identifiers: List of asset identifier strings (e.g. ['ETH', 'BTC',
            'eip155:1/erc20:0x...']).

    Returns:
        Dict with 'assets' (mapping of identifier to metadata including name,
        symbol, asset_type, custom chain address) and 'asset_collections'.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='assets/mappings',
        timeout=cfg.timeout,
        method='POST',
        json_data={'identifiers': identifiers},
    )


@register_tool(name='search_assets')
async def search_assets(
        filter_query: str,
        limit: int = 25,
        search_nfts: bool = False,
) -> dict[str, Any]:
    """Fuzzy-search the global asset database by name or symbol.

    Args:
        filter_query: Search string (name, symbol, or address fragment).
        limit: Maximum number of results (default 25).
        search_nfts: Include NFTs in search results (default false).

    Returns:
        Dict with matching asset identifiers and metadata.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='assets/search/levenshtein',
        timeout=cfg.timeout,
        method='POST',
        json_data={
            'filter_query': filter_query,
            'limit': limit,
            'search_nfts': search_nfts,
        },
    )


@register_tool(name='get_latest_prices')
async def get_latest_prices(
        assets: list[str],
        target_asset: str = 'USD',
) -> dict[str, Any]:
    """Retrieve current prices for specified assets.

    Args:
        assets: List of asset identifiers (e.g. ['ETH', 'BTC', 'eip155:1/erc20:0x...']).
        target_asset: Target currency for prices (default 'USD').

    Returns:
        Dict mapping assets to their current prices in the target asset.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='assets/prices/latest',
        timeout=cfg.timeout,
        method='POST',
        json_data={
            'assets': assets,
            'target_asset': target_asset,
        },
    )


@register_tool(name='get_historical_prices')
async def get_historical_prices(
        assets_timestamp: list[list[Any]],
        target_asset: str = 'USD',
) -> dict[str, Any]:
    """Retrieve historical prices for assets at specific timestamps.

    Args:
        assets_timestamp: List of [asset_identifier, timestamp_seconds] pairs.
            Example: [['ETH', 1609459200], ['BTC', 1609545600]].
        target_asset: Target currency for prices (default 'USD').

    Returns:
        Dict with prices keyed by asset and timestamp.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='assets/prices/historical',
        timeout=cfg.timeout,
        method='POST',
        json_data={
            'assets_timestamp': assets_timestamp,
            'target_asset': target_asset,
        },
    )


@register_tool(name='get_asset_types')
async def get_asset_types() -> dict[str, Any]:
    """Retrieve all supported asset types in the global database."""
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='assets/types',
        timeout=cfg.timeout,
    )
