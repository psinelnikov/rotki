import asyncio
from typing import Any

from rotkehlchen.mcp.backend import get_backend_config, request_api
from rotkehlchen.mcp.registry import register_tool


@register_tool(name='get_blockchain_accounts')
async def get_blockchain_accounts(
        blockchain: str | None = None,
) -> dict[str, Any]:
    """Retrieve blockchain accounts tracked by the user.

    Args:
        blockchain: Optional chain identifier (e.g. 'eth', 'btc', 'optimism',
            'polygon_pos', 'arbitrum_one', 'base', 'solana'). If omitted,
            returns accounts for all chains.

    Returns:
        Dict mapping chain identifiers to lists of tracked addresses/accounts.
    """
    cfg = get_backend_config()
    if blockchain is not None:
        endpoint = f'blockchains/{blockchain}/accounts'
    else:
        endpoint = 'blockchains'
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint=endpoint,
        timeout=cfg.timeout,
    )


@register_tool(name='get_supported_chains')
async def get_supported_chains() -> dict[str, Any]:
    """Retrieve all blockchains supported by rotki with their identifiers."""
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='blockchains/supported',
        timeout=cfg.timeout,
    )


@register_tool(name='get_eth2_validators')
async def get_eth2_validators() -> dict[str, Any]:
    """Retrieve Ethereum 2.0 validators tracked by the user.

    Returns:
        List of validators with their indices, public keys, and status.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='blockchains/eth2/validators',
        timeout=cfg.timeout,
        params={'async_query': False},
    )


@register_tool(name='get_configured_exchanges')
async def get_configured_exchanges() -> dict[str, Any]:
    """Retrieve all configured exchange integrations.

    Returns:
        List of configured exchanges with their names, locations, and API key status.
    """
    cfg = get_backend_config()
    return await asyncio.to_thread(
        request_api,
        base_url=cfg.base_url,
        endpoint='exchanges',
        timeout=cfg.timeout,
    )
