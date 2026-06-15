import asyncio
from typing import Any

from rotkehlchen.mcp.backend import get_backend_config, request_api
from rotkehlchen.mcp.registry import register_tool


@register_tool(name='list_reports')
async def list_reports() -> dict[str, Any]:
    """List all generated PnL / tax accounting reports.

    Each report covers a time range and contains calculated profit/loss data.

    Returns:
        Dict with 'entries' (list of reports with start/end timestamps,
        tax-free/total PnL, currency), 'entries_found', and 'entries_limit'.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='reports',
        timeout=cfg.timeout,
    )


@register_tool(name='get_report_data')
async def get_report_data(
        report_id: int,
        from_timestamp: int = 0,
        to_timestamp: int = 0,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by_attributes: list[str] | None = None,
        ascending: bool = True,
) -> dict[str, Any]:
    """Retrieve detailed accounting event data from a specific PnL report.

    This is the primary tool for analyzing profit/loss breakdown. Each entry
    shows the event's taxable and tax-free PnL amounts.

    Args:
        report_id: The report identifier (from list_reports).
        from_timestamp: Filter events from this timestamp (seconds). 0 = report start.
        to_timestamp: Filter events until this timestamp (seconds). 0 = report end.
        event_type: Filter by accounting event type. Valid values:
            'accounting', 'tx_with_profit', 'tx_with_loss', 'asset_movement',
            'margin_position', 'loan_position', 'staking', 'history_event'.
        limit: Maximum entries to return (default 100).
        offset: Number of entries to skip for pagination.
        order_by_attributes: Sort fields: 'timestamp', 'pnl_taxable',
            'pnl_free', 'asset' (default ['timestamp']).
        ascending: Sort order (default oldest first).

    Returns:
        Dict with 'entries' (accounting events with pnl_taxable, pnl_free,
        asset, amount, notes), 'entries_found', 'entries_total', 'entries_limit'.
    """
    cfg = get_backend_config()
    body: dict[str, Any] = {
        'report_id': report_id,
        'limit': limit,
        'offset': offset,
        'order_by_attributes': order_by_attributes or ['timestamp'],
        'ascending': [ascending],
    }
    if from_timestamp > 0:
        body['from_timestamp'] = from_timestamp
    if to_timestamp > 0:
        body['to_timestamp'] = to_timestamp
    if event_type is not None:
        body['event_type'] = event_type
    if order_by_attributes:
        body['order_by_attributes'] = order_by_attributes

    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint=f'reports/{report_id}/data',
        timeout=cfg.timeout,
        method='POST',
        json_data=body,
    )


@register_tool(name='get_accounting_rules')
async def get_accounting_rules(
        limit: int = 100,
        offset: int = 0,
) -> dict[str, Any]:
    """Retrieve the user's accounting rules that map event types to accounting treatment.

    These rules determine how each type of history event is treated for
    profit/loss calculation (taxable vs. free, cost basis tracking, etc.).

    Args:
        limit: Maximum entries to return (default 100).
        offset: Number of entries to skip for pagination.

    Returns:
        Dict with 'entries' (accounting rules), 'entries_found',
        'entries_total', 'entries_limit'.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='accounting/rules',
        timeout=cfg.timeout,
        method='POST',
        json_data={
            'limit': limit,
            'offset': offset,
        },
    )


@register_tool(name='get_accounting_rule_conflicts')
async def get_accounting_rule_conflicts() -> dict[str, Any]:
    """Retrieve unresolved accounting rule conflicts that need user attention.

    Conflicts occur when multiple accounting rules could apply to the same
    event type combination.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='accounting/rules/conflicts',
        timeout=cfg.timeout,
        method='POST',
        json_data={},
    )
