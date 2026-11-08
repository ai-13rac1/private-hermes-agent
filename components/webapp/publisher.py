"""Fixed-destination TCP bridge; no HTTP routing, DNS, files, or command execution."""
import asyncio
import ipaddress
import sys


async def bridge(reader, writer):
    remote_writer = None
    try:
        remote_reader, remote_writer = await asyncio.open_connection(target, target_port)
        async def copy(source, destination):
            try:
                while data := await source.read(65536):
                    destination.write(data)
                    await destination.drain()
            finally:
                if destination.can_write_eof():
                    destination.write_eof()
        await asyncio.gather(copy(reader, remote_writer), copy(remote_reader, writer))
    except (OSError, asyncio.IncompleteReadError):
        pass
    finally:
        writer.close()
        if remote_writer:
            remote_writer.close()


async def main():
    server = await asyncio.start_server(bridge, '0.0.0.0', listen)
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    listen, target, target_port = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
    ipaddress.IPv4Address(target)  # literal destinations only
    asyncio.run(main())
