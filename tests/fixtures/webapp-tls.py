"""TLS termination fixture for Funnel's HTTPS semantics; no Tailscale enrollment."""
import asyncio
import ssl

async def bridge(reader, writer):
    upstream_reader, upstream_writer = await asyncio.open_connection('10.203.87.3', 8443)
    async def copy(source, destination):
        while data := await source.read(65536):
            destination.write(data)
            await destination.drain()
    try:
        await asyncio.gather(copy(reader, upstream_writer), copy(upstream_reader, writer))
    finally:
        writer.close()
        upstream_writer.close()


async def main():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('/run/test-tls/cert.pem', '/run/test-tls/key.pem')
    server = await asyncio.start_server(bridge, '0.0.0.0', 10000, ssl=context)
    async with server:
        await server.serve_forever()

asyncio.run(main())
