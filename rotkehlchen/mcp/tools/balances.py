import asyncio
from typing import Any

from rotkehlchen.mcp.backend import get_backend_config, request_api
from rotkehlchen.mcp.registry import register_tool


@register_tool(name='get_all_balances')
async def get_all_balances() -> dict[str, Any]:
    """Retrieve the user's complete balance overview across all locations.

    Returns total net worth, per-asset balances, per-location breakdown,
    and liability information. This is the most comprehensive current
    balance snapshot available.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='balances',
        timeout=cfg.timeout,
        params={'async_query': False, 'ignore_cache': False},
    )


@register_tool(name='get_blockchain_balances')
async def get_blockchain_balances(
        blockchain: str | None = None,
) -> dict[str, Any]:
    """Retrieve balances from blockchain accounts.

    Args:
        blockchain: Optional specific chain (e.g. 'eth', 'btc', 'optimism',
            'polygon_pos', 'arbitrum_one'). If omitted, returns all chains.

    Returns:
        Per-chain asset balances with USD values.
    """
    cfg = get_backend_config()
    endpoint = 'balances/blockchains'
    if blockchain is not None:
        endpoint = f'balances/blockchains/{blockchain}'
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint=endpoint,
        timeout=cfg.timeout,
        params={'async_query': False},
    )


@register_tool(name='get_manual_balances')
async def get_manual_balances() -> dict[str, Any]:
    """Retrieve manually tracked balances (user-added, not from exchanges or chains)."""
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='balances/manual',
        timeout=cfg.timeout,
        params={'async_query': False},
    )


@register_tool(name='get_exchange_balances')
async def get_exchange_balances(
        location: str | None = None,
) -> dict[str, Any]:
    """Retrieve balances from configured exchanges.

    Args:
        location: Optional exchange location (e.g. 'kraken', 'binance',
            'coinbase'). If omitted, returns all exchanges.

    Returns:
        Per-exchange asset balances with USD values.
    """
    cfg = get_backend_config()
    endpoint = 'exchanges/balances'
    if location is not None:
        endpoint = f'exchanges/balances/{location}'
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint=endpoint,
        timeout=cfg.timeout,
        params={'async_query': False},
    )


@register_tool(name='get_historical_net_value')
async def get_historical_net_value(
        from_timestamp: int = 0,
        to_timestamp: int = 0,
) -> dict[str, Any]:
    """Retrieve daily historical net value breakdown across all assets.

    Provides a time series of net worth broken down by asset for each day
    in the specified range. Useful for long-term portfolio analysis.

    Args:
        from_timestamp: Unix timestamp (seconds) for start. 0 = beginning.
        to_timestamp: Unix timestamp (seconds) for end. 0 = now.

    Returns:
        Dict with 'times' (list of timestamps) and 'values' (list of
        {asset_id: amount} dicts), plus 'processing_required' flag.
    """
    cfg = get_backend_config()
    body: dict[str, Any] = {}
    if from_timestamp > 0:
        body['from_timestamp'] = from_timestamp
    if to_timestamp > 0:
        body['to_timestamp'] = to_timestamp
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='balances/historical/netvalue',
        timeout=cfg.timeout,
        method='POST',
        json_data=body,
    )


@register_tool(name='get_historical_asset_balance')
async def get_historical_asset_balance(
        asset: str | None = None,
        collection_id: str | None = None,
        from_timestamp: int = 0,
        to_timestamp: int = 0,
) -> dict[str, Any]:
    """Retrieve historical balance time series for a specific asset or collection.

    Args:
        asset: Asset identifier (e.g. 'ETH'). Either this or collection_id required.
        collection_id: Asset collection identifier. Either this or asset required.
        from_timestamp: Unix timestamp (seconds) for start. 0 = beginning.
        to_timestamp: Unix timestamp (seconds) for end. 0 = now.

    Returns:
        Dict with 'entries' containing 'times' and 'values' arrays.
    """
    cfg = get_backend_config()
    body: dict[str, Any] = {}
    if from_timestamp > 0:
        body['from_timestamp'] = from_timestamp
    if to_timestamp > 0:
        body['to_timestamp'] = to_timestamp
    if asset is not None:
        body['asset'] = asset
    if collection_id is not None:
        body['collection_id'] = collection_id
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='balances/historical/asset/series',
        timeout=cfg.timeout,
        method='POST',
        json_data=body,
    )
