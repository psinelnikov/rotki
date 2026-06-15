import asyncio
from typing import Any

from rotkehlchen.mcp.backend import BackendQueryError, get_backend_config, request_api
from rotkehlchen.mcp.registry import register_tool


@register_tool(name='get_unmatched_asset_movements')
async def get_unmatched_asset_movements(
        only_ignored: bool = False,
) -> dict[str, Any]:
    """Retrieve asset movements (deposits/withdrawals) that have no matching on-chain event.

    Returns group identifiers for unmatched exchange deposits/withdrawals.
    Use get_asset_movement_details to get full information for a specific movement,
    or find_asset_movement_matches to find candidate on-chain events.

    Args:
        only_ignored: If true, return only previously ignored movements.

    Returns:
        Dict with 'result' being a list of group identifier strings.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='history/events/match/asset_movements',
        timeout=cfg.timeout,
        params={'only_ignored': only_ignored},
    )


@register_tool(name='get_asset_movement_details')
async def get_asset_movement_details(
        group_identifier: str,
) -> dict[str, Any]:
    """Get full details for a specific asset movement by its group identifier.

    Returns the numeric event identifier, asset, amount, location, timestamp,
    and type (deposit/withdrawal/fee) for the movement. The numeric identifier
    is needed for find_asset_movement_matches and match_asset_movement.

    Args:
        group_identifier: The group identifier string from get_unmatched_asset_movements.

    Returns:
        Dict with event details including 'identifier' (numeric ID), 'asset',
        'amount', 'location', 'event_subtype', and 'timestamp'.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='history/events',
        timeout=cfg.timeout,
        method='POST',
        json_data={
            'group_identifiers': [group_identifier],
            'limit': 10,
            'offset': 0,
            'order_by_attributes': ['timestamp'],
            'ascending': [True],
        },
    )


@register_tool(name='find_asset_movement_matches')
async def find_asset_movement_matches(
        asset_movement: str,
        time_range: int = 3600,
        only_expected_assets: bool = True,
        tolerance: float = 0.1,
) -> dict[str, Any]:
    """Find possible on-chain event matches for an unmatched asset movement.

    Searches for history events that could correspond to the given asset
    movement (deposit/withdrawal) within a time window.

    Args:
        asset_movement: The group identifier of the asset movement (from
            get_unmatched_asset_movements).
        time_range: Time window in seconds to search around the movement (default 3600).
        only_expected_assets: Only suggest matches with the same asset (default true).
        tolerance: Allowed amount difference as a fraction (default 0.1 = 10%).

    Returns:
        Dict with 'close_matches' (list of numeric event IDs that are likely matches)
        and 'other_events' (list of numeric event IDs that are possible candidates).
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='history/events/match/asset_movements',
        timeout=cfg.timeout,
        method='POST',
        json_data={
            'asset_movement': asset_movement,
            'time_range': time_range,
            'only_expected_assets': only_expected_assets,
            'tolerance': tolerance,
        },
    )


def _resolve_and_match(
        group_identifier: str,
        matched_events: list[int],
        timeout: int,
        base_url: str,
) -> dict[str, Any]:
    """Resolve the numeric event ID from the group identifier, then call the match API."""
    events = request_api(
        base_url=base_url,
        endpoint='history/events',
        timeout=timeout,
        method='POST',
        json_data={
            'group_identifiers': [group_identifier],
            'limit': 10,
            'offset': 0,
        },
    )
    movement_id: int | None = None
    for entry in events.get('result', {}).get('entries', []):
        event = entry.get('entry', entry)
        if event.get('entry_type') == 'asset movement event' or event.get('event_type') == 'exchange transfer':  # noqa: E501
            movement_id = event.get('identifier')
            break
    if movement_id is None:
        raise BackendQueryError(
            f'Could not find asset movement event with group identifier {group_identifier}',
        )
    return request_api(
        base_url=base_url,
        endpoint='history/events/match/asset_movements',
        timeout=timeout,
        method='PUT',
        json_data={
            'asset_movement': movement_id,
            'matched_events': matched_events,
        },
    )


@register_tool(name='match_asset_movement')
async def match_asset_movement(
        asset_movement: str,
        matched_events: list[int],
) -> dict[str, Any]:
    """Link an asset movement to specific on-chain history events.

    Pass an empty list to mark the movement as having no match (ignores it).

    Args:
        asset_movement: The group identifier of the asset movement (from
            get_unmatched_asset_movements). The numeric ID is resolved automatically.
        matched_events: List of numeric event IDs to link (from find_asset_movement_matches
            close_matches or other_events). Pass an empty list to ignore the movement.

    Returns:
        Confirmation of the match operation.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        _resolve_and_match,
        asset_movement, matched_events, cfg.timeout, cfg.base_url,
    )


@register_tool(name='unlink_asset_movement')
async def unlink_asset_movement(identifier: int) -> dict[str, Any]:
    """Remove the match link from a previously matched asset movement.

    Args:
        identifier: The numeric event identifier of the matched asset movement.

    Returns:
        Confirmation of the unlink operation.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='history/events/match/asset_movements',
        timeout=cfg.timeout,
        method='DELETE',
        json_data={'identifier': identifier},
    )
