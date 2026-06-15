import asyncio
from typing import Any

from rotkehlchen.mcp.backend import get_backend_config, request_api
from rotkehlchen.mcp.registry import register_tool


def _query_events(
        from_timestamp: int,
        to_timestamp: int,
        asset: str | None,
        event_types: list[str] | None,
        event_subtypes: list[str] | None,
        counterparties: list[str] | None,
        location: str | None,
        location_labels: list[str] | None,
        addresses: list[str] | None,
        group_identifiers: list[str] | None,
        exclude_ignored_assets: bool,
        aggregate_by_group_ids: bool,
        limit: int,
        offset: int,
        ascending: bool,
) -> dict[str, Any]:
    cfg = get_backend_config()
    body: dict[str, Any] = {
        'limit': limit,
        'offset': offset,
        'order_by_attributes': ['timestamp'],
        'ascending': [ascending],
    }
    if from_timestamp > 0:
        body['from_timestamp'] = from_timestamp
    if to_timestamp > 0:
        body['to_timestamp'] = to_timestamp
    if asset is not None:
        body['asset'] = asset
    if event_types:
        body['event_types'] = event_types
    if event_subtypes:
        body['event_subtypes'] = event_subtypes
    if counterparties:
        body['counterparties'] = counterparties
    if location is not None:
        body['location'] = location
    if location_labels:
        body['location_labels'] = location_labels
    if addresses:
        body['addresses'] = addresses
    if group_identifiers:
        body['group_identifiers'] = group_identifiers
    body['exclude_ignored_assets'] = exclude_ignored_assets
    body['aggregate_by_group_ids'] = aggregate_by_group_ids
    return request_api(
        base_url=cfg.base_url,
        endpoint='history/events',
        timeout=cfg.timeout,
        method='POST',
        json_data=body,
    )


@register_tool(name='query_history_events')
async def query_history_events(
        from_timestamp: int = 0,
        to_timestamp: int = 0,
        asset: str | None = None,
        event_types: list[str] | None = None,
        event_subtypes: list[str] | None = None,
        counterparties: list[str] | None = None,
        location: str | None = None,
        location_labels: list[str] | None = None,
        addresses: list[str] | None = None,
        group_identifiers: list[str] | None = None,
        exclude_ignored_assets: bool = True,
        aggregate_by_group_ids: bool = False,
        limit: int = 100,
        offset: int = 0,
        ascending: bool = True,
) -> dict[str, Any]:
    """Query and filter the user's history events.

    This is the primary tool for retrieving accounting data. History events
    are the core abstraction covering all blockchain, exchange, and manual
    activities (trades, deposits, withdrawals, staking, swaps, etc.).

    Args:
        from_timestamp: Unix timestamp (seconds) for the start of the range. 0 = beginning.
        to_timestamp: Unix timestamp (seconds) for the end. 0 = now.
        asset: Filter to a single asset identifier (e.g. 'ETH', 'eip155:1/erc20:0x...').
        event_types: Filter by event types (e.g. ['trade', 'staking', 'receive', 'spend']).
        event_subtypes: Filter by subtypes (e.g. ['reward', 'fee', 'deposit asset']).
        counterparties: Filter by protocol/exchange IDs (e.g. ['uniswap-v2', 'aave', 'kraken']).
        location: Filter by location enum (e.g. 'blockchain', 'kraken', 'binance', 'external').
        location_labels: Filter by location labels (typically wallet addresses or exchange IDs).
        addresses: Filter by EVM/Solana/BTC addresses involved.
        group_identifiers: Filter by specific event group IDs (transaction hashes).
        exclude_ignored_assets: Exclude assets marked as ignored by the user.
        aggregate_by_group_ids: Collapse grouped events into single entries.
        limit: Maximum number of events to return (default 100).
        offset: Number of events to skip for pagination.
        ascending: Sort order by timestamp (default oldest first).

    Returns:
        Dict with 'entries' (list of serialized events), 'entries_found' (total
        matching), 'entries_limit', and 'entries_total'.
    """
    return await asyncio.to_thread(
        _query_events,
        from_timestamp, to_timestamp, asset, event_types, event_subtypes,
        counterparties, location, location_labels, addresses, group_identifiers,
        exclude_ignored_assets, aggregate_by_group_ids, limit, offset, ascending,
    )


@register_tool(name='get_event_type_mappings')
async def get_event_type_mappings() -> dict[str, Any]:
    """Return mappings of event types/subtypes to accounting categories.

    Use this to understand how different event types are classified for
    accounting purposes. Includes global mappings, entry type mappings,
    event category details, and accounting event icons.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='history/events/type_mappings',
        timeout=cfg.timeout,
    )


@register_tool(name='get_counterparties')
async def get_counterparties() -> dict[str, Any]:
    """Return all known counterparties (protocols, exchanges) with labels and icons.

    Useful for finding the correct counterparty identifier to pass to
    query_history_events.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='history/events/counterparties',
        timeout=cfg.timeout,
    )


@register_tool(name='get_event_details')
async def get_event_details(identifier: int) -> dict[str, Any]:
    """Get detailed information about a specific history event by its identifier.

    Args:
        identifier: The numeric event identifier.

    Returns:
        Detailed event data including decoded transaction information.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='history/events/details',
        timeout=cfg.timeout,
        params={'identifier': identifier},
    )
