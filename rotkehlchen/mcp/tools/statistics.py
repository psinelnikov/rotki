import asyncio
from typing import Any

from rotkehlchen.mcp.backend import get_backend_config, request_api
from rotkehlchen.mcp.registry import register_tool


@register_tool(name='get_net_value')
async def get_net_value(include_nfts: bool = True) -> dict[str, Any]:
    """Retrieve the user's net worth time series.

    Returns cumulative net value over time, useful for tracking portfolio
    growth. Free tier data is limited to the most recent 14 days.

    Args:
        include_nfts: Include NFT valuations in net worth (default true).

    Returns:
        Dict with 'times' (timestamps) and 'data' (net worth values).
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='statistics/netvalue',
        timeout=cfg.timeout,
        params={'include_nfts': include_nfts},
    )


@register_tool(name='get_value_distribution')
async def get_value_distribution(
        distribution_by: str = 'location',
) -> dict[str, Any]:
    """Retrieve balance distribution breakdown.

    Args:
        distribution_by: Grouping method: 'location' (by exchange/chain/etc.)
            or 'asset' (by individual asset).

    Returns:
        Dict with distribution data showing how wealth is spread across
        locations or assets.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='statistics/value_distribution',
        timeout=cfg.timeout,
        params={'distribution_by': distribution_by},
    )


@register_tool(name='get_statistics_asset_balance')
async def get_statistics_asset_balance(
        asset: str | None = None,
        collection_id: str | None = None,
        from_timestamp: int = 0,
        to_timestamp: int = 0,
) -> dict[str, Any]:
    """Retrieve timed balance entries for a specific asset over a time range.

    Args:
        asset: Asset identifier (e.g. 'ETH'). Either this or collection_id required.
        collection_id: Asset collection identifier.
        from_timestamp: Unix timestamp (seconds) for start. 0 = beginning.
        to_timestamp: Unix timestamp (seconds) for end. 0 = now.

    Returns:
        List of timed balance entries showing the asset amount at each point.
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
        endpoint='statistics/balance',
        timeout=cfg.timeout,
        method='POST',
        json_data=body,
    )


@register_tool(name='get_history_status_summary')
async def get_history_status_summary() -> dict[str, Any]:
    """Retrieve data freshness and processing status.

    Shows when blockchain and exchange data was last queried, how many
    undecoded transactions exist, and whether the user has connected
    blockchain or exchange accounts.

    Returns:
        Dict with 'evm_last_queried_ts', 'exchanges_last_queried_ts',
        'undecoded_tx_count', 'has_evm_accounts', 'has_exchanges_accounts'.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='history/status/summary',
        timeout=cfg.timeout,
    )


@register_tool(name='get_actionable_items')
async def get_actionable_items() -> dict[str, Any]:
    """Retrieve history items needing user attention.

    Includes unmatched asset movements, decoding failures, and other
    items that may require manual review for accurate accounting.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='history/actionable_items',
        timeout=cfg.timeout,
    )


@register_tool(name='get_periodic_data')
async def get_periodic_data() -> dict[str, Any]:
    """Retrieve periodic summary data (last balance save, processing status, etc.).

    Returns:
        Dict with 'last_balance_save', 'last_data_upload_ts', and other
        periodic metadata.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='periodic',
        timeout=cfg.timeout,
    )
