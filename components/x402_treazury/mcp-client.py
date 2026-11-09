"""Run inside Hermes as its user; no Docker or treasury access."""
import asyncio
import sys


class GatewayPending(RuntimeError):
    pass


async def main():
    if sys.argv[1] == 'reload':
        from hermes_cli.gateway_client import connect_gateway
        from hermes_cli.gateway_runtime import discover_gateway_endpoint, gateway_profile_home, attachable
        from hermes_constants import get_hermes_home
        # Explicit discovery never launches or replaces a gateway process.
        discovery = await asyncio.to_thread(discover_gateway_endpoint, gateway_profile_home(get_hermes_home()))
        if not attachable(discovery):
            if discovery.state in ('starting', 'absent'):
                raise GatewayPending()
            raise RuntimeError('Gateway control endpoint is inaccessible')
        async with connect_gateway(endpoint=discovery.endpoint) as client:
            result = await client.rpc('reload.mcp', confirm=True)
        if result.get('status') != 'reloaded' or any(
                name.startswith('x402_treazury_') for name in result.get('unavailable', [])):
            raise RuntimeError('Hermes could not reload its research MCP clients')
        print('Hermes MCP configuration reloaded; existing sessions and unrelated servers retained.')
    else:
        from hermes_cli.config import load_env
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client, create_mcp_http_client
        token = load_env()['X402_TREAZURY_MCP_TOKEN']
        for port in range(3010, 3022):
            async with create_mcp_http_client(headers={'Authorization': 'Bearer ' + token}) as client:
                async with streamable_http_client(f'http://127.0.0.1:{port}/mcp', http_client=client) as (read, write, *_):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        await session.list_tools()
        print('All twelve authenticated MCP endpoints initialized and listed successfully.')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as error:
        # Do not print client objects, headers, or raw protocol responses.
        print('MCP operation unavailable (' + type(error).__name__ + ')', file=sys.stderr)
        def temporary(exc):
            if hasattr(exc, 'exceptions'):
                return all(temporary(child) for child in exc.exceptions)
            response = getattr(exc, 'response', None)
            if response is not None:
                return response.status_code in (502, 503, 504)
            return type(exc).__name__ in ('ConnectError', 'ConnectTimeout', 'ReadTimeout', 'ReadError')
        transient = isinstance(error, GatewayPending) or temporary(error)
        sys.exit(75 if transient else 1)
