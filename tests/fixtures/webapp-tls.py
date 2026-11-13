"""TLS termination fixture for Funnel's HTTPS semantics; no Tailscale enrollment."""
import asyncio
import ssl

async def bridge(reader, writer):
    async def copy(source, destination):
        while data := await source.read(65536):
            destination.write(data)
            await destination.drain()
    writers = [writer]
    copies = []
    try:
        upstream_reader, upstream_writer = await asyncio.open_connection('10.203.87.3', 8443)
        writers.append(upstream_writer)
        copies = [asyncio.create_task(copy(reader, upstream_writer)),
                  asyncio.create_task(copy(upstream_reader, writer))]
        # A closed TLS/browser connection cannot consume further upstream data.
        # Do not leave its other copy pending on a keep-alive upstream socket.
        done, _ = await asyncio.wait(copies, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except (ConnectionResetError, BrokenPipeError):
        pass  # Browser navigation/download cancellation closes connections normally.
    finally:
        for task in copies:
            task.cancel()
        await asyncio.gather(*copies, return_exceptions=True)
        for connection in writers:
            connection.close()
        await asyncio.gather(*(connection.wait_closed() for connection in writers), return_exceptions=True)


async def main():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('/run/test-tls/cert.pem', '/run/test-tls/key.pem')
    server = await asyncio.start_server(bridge, '0.0.0.0', 10000, ssl=context)
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
