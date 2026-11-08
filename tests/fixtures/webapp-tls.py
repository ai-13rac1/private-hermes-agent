"""TLS termination fixture for Funnel's HTTPS semantics; no Tailscale enrollment."""
import asyncio
import ssl
import sys
sys.path.insert(0, '/opt')
import publisher
publisher.listen, publisher.target, publisher.target_port = 10000, '10.203.87.3', 8080

async def main():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('/run/test-tls/cert.pem', '/run/test-tls/key.pem')
    server = await asyncio.start_server(publisher.bridge, '0.0.0.0', 10000, ssl=context)
    async with server:
        await server.serve_forever()

asyncio.run(main())
