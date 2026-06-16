import asyncio
import logging
from typing import Any

from rotkehlchen.mcp.backend import BackendQueryError, get_backend_config, request_api
from rotkehlchen.mcp.registry import register_tool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_movement_id(base_url: str, timeout: int, group_id: str) -> int:
    """Resolve a group identifier to the numeric event ID of the asset movement."""
    events = request_api(
        base_url=base_url,
        endpoint='history/events',
        timeout=timeout,
        method='POST',
        json_data={
            'group_identifiers': [group_id],
            'limit': 10,
            'offset': 0,
        },
    )
    for entry in events.get('result', {}).get('entries', []):
        event = entry.get('entry', entry)
        entry_type = event.get('entry_type', '')
        event_type = event.get('event_type', '')
        if 'asset movement' in entry_type or event_type == 'exchange transfer':
            identifier = event.get('identifier')
            if identifier is not None:
                return int(identifier)
    raise BackendQueryError(
        f'Could not find asset movement event ID for group {group_id}',
    )


def _do_match(
        base_url: str,
        timeout: int,
        group_id: str,
        matched_event_ids: list[int],
) -> None:
    """Resolve the movement's numeric ID and call the PUT match endpoint."""
    movement_id = _resolve_movement_id(base_url, timeout, group_id)
    request_api(
        base_url=base_url,
        endpoint='history/events/match/asset_movements',
        timeout=timeout,
        method='PUT',
        json_data={
            'asset_movement': movement_id,
            'matched_events': matched_event_ids,
        },
    )


def _find_matches(
        base_url: str,
        timeout: int,
        group_id: str,
        time_range: int,
        tolerance: float,
) -> dict[str, Any]:
    """Call find_asset_movement_matches for a single group ID."""
    result = request_api(
        base_url=base_url,
        endpoint='history/events/match/asset_movements',
        timeout=timeout,
        method='POST',
        json_data={
            'asset_movement': group_id,
            'time_range': time_range,
            'only_expected_assets': True,
            'tolerance': tolerance,
        },
    )
    return result.get('result', {})


def _classify(close_matches: list[int], other_events: list[int]) -> str:
    """Classify a movement into a resolution tier.

    Returns one of: 'auto_ignore', 'auto_match', 'needs_review'.
    """
    if len(close_matches) == 0 and len(other_events) == 0:
        return 'auto_ignore'
    if len(close_matches) == 1:
        return 'auto_match'
    return 'needs_review'


def _review_reason(close_matches: list[int], other_events: list[int]) -> str:
    if len(close_matches) > 1:
        return f'Multiple close matches ({len(close_matches)}): {close_matches}'
    if len(close_matches) == 0 and len(other_events) > 0:
        return f'No close matches, {len(other_events)} loose candidates: {other_events[:5]}'
    return 'Ambiguous'


# ---------------------------------------------------------------------------
# Auto-resolution engine
# ---------------------------------------------------------------------------

def _auto_resolve(
        dry_run: bool,
        auto_match: bool,
        auto_ignore: bool,
        time_range: int,
        tolerance: float,
        limit: int,
) -> dict[str, Any]:
    cfg = get_backend_config()
    # Use a generous timeout for batch operations
    timeout = max(cfg.timeout, 30)

    # 1. Fetch all unmatched movements
    unmatched = request_api(
        base_url=cfg.base_url,
        endpoint='history/events/match/asset_movements',
        timeout=timeout,
        params={'only_ignored': False},
    )
    group_ids: list[str] = unmatched.get('result', [])
    if limit > 0:
        group_ids = group_ids[:limit]

    report: dict[str, Any] = {
        'dry_run': dry_run,
        'total': len(group_ids),
        'processed': 0,
        'auto_ignored': 0,
        'auto_matched': 0,
        'needs_review': 0,
        'errors': 0,
        'matched_details': [],
        'review_details': [],
        'ignored_details': [],
        'error_details': [],
    }

    for group_id in group_ids:
        report['processed'] += 1
        try:
            match_data = _find_matches(
                base_url=cfg.base_url,
                timeout=timeout,
                group_id=group_id,
                time_range=time_range,
                tolerance=tolerance,
            )
            close_matches: list[int] = match_data.get('close_matches', [])
            other_events: list[int] = match_data.get('other_events', [])
            tier = _classify(close_matches, other_events)

            if tier == 'auto_ignore':
                report['auto_ignored'] += 1
                report['ignored_details'].append(group_id)
                if not dry_run and auto_ignore:
                    _do_match(cfg.base_url, timeout, group_id, [])

            elif tier == 'auto_match':
                report['auto_matched'] += 1
                report['matched_details'].append({
                    'group_id': group_id,
                    'event_id': close_matches[0],
                })
                if not dry_run and auto_match:
                    _do_match(cfg.base_url, timeout, group_id, close_matches)

            else:  # needs_review
                report['needs_review'] += 1
                report['review_details'].append({
                    'group_id': group_id,
                    'close_matches': close_matches,
                    'other_events': other_events,
                    'reason': _review_reason(close_matches, other_events),
                })

        except (BackendQueryError, Exception) as e:
            report['errors'] += 1
            report['error_details'].append({
                'group_id': group_id,
                'error': str(e),
            })
            logger.warning('Error processing %s: %s', group_id, e)

    return report


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

@register_tool(name='auto_resolve_asset_movements')
async def auto_resolve_asset_movements(
        dry_run: bool = True,
        auto_match: bool = True,
        auto_ignore: bool = True,
        time_range: int = 3600,
        tolerance: float = 0.1,
        limit: int = 500,
) -> dict[str, Any]:
    """Scan all unmatched asset movements and resolve them with safety guardrails.

    Applies a tiered strategy:
    - AUTO-IGNORE: Movements with zero candidate events (no close_matches,
      no other_events). These are transfers to untracked addresses.
    - AUTO-MATCH: Movements with exactly 1 close_match. These are high
      confidence matches identified by rotki's algorithm.
    - NEEDS REVIEW: Everything else (multiple candidates, only loose matches).
      These are reported but not actioned.

    Always run with dry_run=True first to preview the changes before executing.

    Args:
        dry_run: Preview only — report what would happen without making changes
            (default True). Set to False to execute auto-match and auto-ignore.
        auto_match: Allow auto-matching single close matches (default True).
        auto_ignore: Allow auto-ignoring zero-candidate movements (default True).
        time_range: Time window in seconds for finding matches (default 3600).
        tolerance: Allowed amount difference as a fraction (default 0.1 = 10%).
        limit: Maximum movements to process (default 500, 0 = unlimited).

    Returns:
        Report dict with:
        - 'total', 'processed': movement counts
        - 'auto_ignored', 'auto_matched', 'needs_review', 'errors': per-tier counts
        - 'matched_details': list of {group_id, event_id} for auto-matched
        - 'review_details': list of {group_id, close_matches, other_events, reason}
        - 'ignored_details': list of group IDs that were/would be ignored
        - 'error_details': list of {group_id, error} for failures
    """
    return await asyncio.to_thread(
        _auto_resolve,
        dry_run, auto_match, auto_ignore, time_range, tolerance, limit,
    )


@register_tool(name='get_unmatched_asset_movements')
async def get_unmatched_asset_movements(
        only_ignored: bool = False,
) -> dict[str, Any]:
    """Retrieve asset movements (deposits/withdrawals) that have no matching on-chain event.

    Returns group identifiers for unmatched exchange deposits/withdrawals.
    Use find_asset_movement_matches to find candidate on-chain events,
    or auto_resolve_asset_movements for bulk processing with guardrails.

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
    and type (deposit/withdrawal/fee) for the movement.

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

    Args:
        asset_movement: The group identifier of the asset movement.
        time_range: Time window in seconds to search (default 3600).
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


@register_tool(name='match_asset_movement')
async def match_asset_movement(
        asset_movement: str,
        matched_events: list[int],
) -> dict[str, Any]:
    """Link an asset movement to specific on-chain history events.

    Pass an empty list to mark the movement as having no match (ignores it).

    Args:
        asset_movement: The group identifier of the asset movement.
            The numeric ID is resolved automatically.
        matched_events: List of numeric event IDs to link (from
            find_asset_movement_matches close_matches). Empty list = ignore.

    Returns:
        Confirmation of the match operation.
    """
    cfg = get_backend_config()
    timeout = max(cfg.timeout, 30)
    return await asyncio.to_thread(
        lambda: request_api(
            base_url=cfg.base_url,
            endpoint='history/events/match/asset_movements',
            timeout=timeout,
            method='PUT',
            json_data={
                'asset_movement': _resolve_movement_id(cfg.base_url, timeout, asset_movement),
                'matched_events': matched_events,
            },
        ),
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
