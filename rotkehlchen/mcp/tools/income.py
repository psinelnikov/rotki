import asyncio
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from rotkehlchen.mcp.backend import get_backend_config, request_api
from rotkehlchen.mcp.registry import register_tool


def _fetch_receive_events(
        base_url: str,
        timeout: int,
        from_ts: int,
        to_ts: int,
        event_types: list[str],
        limit: int,
) -> list[dict[str, Any]]:
    """Fetch receive-type events in paginated batches."""
    all_events: list[dict[str, Any]] = []
    offset = 0
    batch_size = min(limit, 500)

    while len(all_events) < limit:
        body: dict[str, Any] = {
            'event_types': event_types,
            'limit': batch_size,
            'offset': offset,
            'order_by_attributes': ['timestamp'],
            'ascending': [True],
        }
        if from_ts > 0:
            body['from_timestamp'] = from_ts
        if to_ts > 0:
            body['to_timestamp'] = to_ts

        result = request_api(
            base_url=base_url,
            endpoint='history/events',
            timeout=timeout,
            method='POST',
            json_data=body,
        )
        entries = result.get('result', {}).get('entries', [])
        if not entries:
            break

        for entry in entries:
            event = entry.get('entry', entry)
            all_events.append(event)

        if len(entries) < batch_size:
            break
        offset += batch_size

    return all_events[:limit]


def _get_prices(
        base_url: str,
        timeout: int,
        assets: list[str],
        target_asset: str,
) -> dict[str, float]:
    """Fetch current prices for a list of assets."""
    if not assets:
        return {}
    result = request_api(
        base_url=base_url,
        endpoint='assets/prices/latest',
        timeout=timeout,
        method='POST',
        json_data={
            'assets': assets,
            'target_asset': target_asset,
        },
    )
    raw_prices = result.get('result', {})
    if isinstance(raw_prices, dict):
        return {k: float(v) for k, v in raw_prices.items() if v is not None}
    return {}


def _build_income_report(
        events: list[dict[str, Any]],
        prices: dict[str, float],
        target_asset: str,
) -> dict[str, Any]:
    """Aggregate events into an income report grouped by asset and month."""
    asset_totals: dict[str, float] = defaultdict(float)
    asset_counts: dict[str, int] = defaultdict(int)
    monthly_totals: dict[str, float] = defaultdict(float)
    monthly_counts: dict[str, int] = defaultdict(int)
    location_totals: dict[str, float] = defaultdict(float)
    first_ts: int | None = None
    last_ts: int | None = None

    for event in events:
        asset = event.get('asset', 'UNKNOWN')
        try:
            amount = float(event.get('amount', 0))
        except (TypeError, ValueError):
            amount = 0.0

        if amount <= 0:
            continue

        ts_ms = event.get('timestamp', 0)
        # timestamps from rotki are in milliseconds
        ts_sec = ts_ms // 1000 if ts_ms > 10**12 else ts_ms
        month_key = datetime.fromtimestamp(ts_sec, tz=UTC).strftime('%Y-%m')

        price = prices.get(asset, 0.0)
        value = amount * price

        asset_totals[asset] += amount
        asset_counts[asset] += 1
        monthly_totals[month_key] += value
        monthly_counts[month_key] += 1

        location = event.get('location', 'unknown')
        location_totals[location] += value

        if first_ts is None or ts_sec < first_ts:
            first_ts = ts_sec
        if last_ts is None or ts_sec > last_ts:
            last_ts = ts_sec

    # Build per-asset breakdown sorted by value descending
    per_asset = []
    total_value = 0.0
    for asset, amount in sorted(asset_totals.items(), key=lambda x: -x[1]):
        price = prices.get(asset, 0.0)
        value = amount * price
        total_value += value
        per_asset.append({
            'asset': asset,
            'total_amount': amount,
            'event_count': asset_counts[asset],
            'current_price': price,
            'current_value': round(value, 2),
        })

    # Monthly breakdown
    per_month = []
    for month in sorted(monthly_totals.keys()):
        per_month.append({
            'month': month,
            'value': round(monthly_totals[month], 2),
            'event_count': monthly_counts[month],
        })

    # Location breakdown
    per_location = []
    for location in sorted(location_totals.keys(), key=lambda l: -location_totals[l]):
        per_location.append({
            'location': location,
            'value': round(location_totals[location], 2),
        })

    return {
        'target_asset': target_asset,
        'total_events': len(events),
        'total_current_value': round(total_value, 2),
        'date_range': {
            'from': first_ts,
            'to': last_ts,
        },
        'per_asset': per_asset,
        'per_month': per_month,
        'per_location': per_location,
    }


def _get_income_summary(
        from_ts: int,
        to_ts: int,
        target_asset: str,
        include_staking: bool,
        include_airdrops: bool,
        limit: int,
) -> dict[str, Any]:
    cfg = get_backend_config()
    timeout = max(cfg.timeout, 30)

    # Build event type filter
    event_types = ['receive', 'exchange transfer']
    # We'll filter subtypes after fetching, since the API accepts event_types list

    events = _fetch_receive_events(
        base_url=cfg.base_url,
        timeout=timeout,
        from_ts=from_ts,
        to_ts=to_ts,
        event_types=event_types,
        limit=limit,
    )

    # Filter by subtype
    valid_subtypes = {'receive'}
    if include_staking:
        valid_subtypes.add('reward')
    if include_airdrops:
        valid_subtypes.add('airdrop')

    # Also include staking-type events if requested
    if include_staking:
        staking_events = _fetch_receive_events(
            base_url=cfg.base_url,
            timeout=timeout,
            from_ts=from_ts,
            to_ts=to_ts,
            event_types=['staking'],
            limit=limit,
        )
        events.extend(staking_events)

    filtered = [
        e for e in events
        if e.get('event_subtype', '').lower() in valid_subtypes
    ]

    # Get current prices for all assets
    assets = list({e.get('asset') for e in filtered if e.get('asset')})
    prices = _get_prices(cfg.base_url, timeout, assets, target_asset)

    # Build report
    return _build_income_report(filtered, prices, target_asset)


@register_tool(name='get_crypto_income_summary')
async def get_crypto_income_summary(
        from_timestamp: int = 0,
        to_timestamp: int = 0,
        target_asset: str = 'USD',
        include_staking: bool = False,
        include_airdrops: bool = False,
        limit: int = 1000,
) -> dict[str, Any]:
    """Analyze all crypto received as income and calculate total value.

    Queries deposit/receive events and produces a comprehensive income report
    with current market valuations, per-asset breakdown, monthly trends, and
    location distribution.

    Args:
        from_timestamp: Unix timestamp (seconds) for start. 0 = beginning.
        to_timestamp: Unix timestamp (seconds) for end. 0 = now.
        target_asset: Currency for valuations (default 'USD').
        include_staking: Include staking rewards as income (default false).
        include_airdrops: Include airdrop receipts as income (default false).
        limit: Maximum events to analyze (default 1000).

    Returns:
        Income report with:
        - 'total_current_value': total value of all received crypto
        - 'per_asset': breakdown by asset (amount, price, value, count)
        - 'per_month': monthly value trend
        - 'per_location': value by source location
        - 'date_range': first and last event timestamps
    """
    return await asyncio.to_thread(
        _get_income_summary,
        from_timestamp, to_timestamp, target_asset,
        include_staking, include_airdrops, limit,
    )


@register_tool(name='get_crypto_income_events')
async def get_crypto_income_events(
        from_timestamp: int = 0,
        to_timestamp: int = 0,
        asset: str | None = None,
        limit: int = 100,
        offset: int = 0,
) -> dict[str, Any]:
    """Retrieve individual crypto deposit/receive events for income tracking.

    Returns the raw event details for each crypto received, useful for
    auditing specific deposits or building custom reports.

    Args:
        from_timestamp: Unix timestamp (seconds) for start. 0 = beginning.
        to_timestamp: Unix timestamp (seconds) for end. 0 = now.
        asset: Filter to a specific asset identifier.
        limit: Maximum events (default 100).
        offset: Pagination offset.

    Returns:
        Dict with 'entries' (list of receive events with timestamp, asset,
        amount, location, counterparty, notes) and 'entries_found'.
    """
    cfg = get_backend_config()
    body: dict[str, Any] = {
        'event_types': ['receive', 'exchange transfer'],
        'event_subtypes': ['receive'],
        'limit': limit,
        'offset': offset,
        'order_by_attributes': ['timestamp'],
        'ascending': [False],
    }
    if from_timestamp > 0:
        body['from_timestamp'] = from_timestamp
    if to_timestamp > 0:
        body['to_timestamp'] = to_timestamp
    if asset is not None:
        body['asset'] = asset

    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='history/events',
        timeout=max(cfg.timeout, 30),
        method='POST',
        json_data=body,
    )
