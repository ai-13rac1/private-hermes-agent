"""Real socket delivery and peer-closure behavior of the simulated TLS bridge."""
import asyncio
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'webapp_tls_fixture', Path(__file__).parent / 'fixtures/webapp-tls.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class TLSBridgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_bidirectional_bytes_and_either_peer_closure(self):
        real_connect = asyncio.open_connection
        for upstream_closes in (False, True):
            with self.subTest(upstream_closes=upstream_closes):
                request, response = b'client' * 20000, b'upstream' * 20000
                received, errors = [], []
                upstream_done, bridge_done = asyncio.Event(), asyncio.Event()

                async def upstream(reader, writer):
                    try:
                        received.append(await reader.readexactly(len(request)))
                        writer.write(response)
                        await writer.drain()
                        if not upstream_closes:
                            received.append(await reader.read())
                    except Exception as error:
                        errors.append(error)
                    finally:
                        writer.close()
                        await writer.wait_closed()
                        upstream_done.set()

                async def bridge(reader, writer):
                    try:
                        await fixture.bridge(reader, writer)
                    except Exception as error:
                        errors.append(error)
                    finally:
                        bridge_done.set()

                async with await asyncio.start_server(upstream, '127.0.0.1', 0) as server:
                    address = server.sockets[0].getsockname()
                    async def connect_upstream(*_):
                        return await real_connect(*address)
                    with patch.object(fixture.asyncio, 'open_connection',
                                      side_effect=connect_upstream):
                        async with await asyncio.start_server(bridge, '127.0.0.1', 0) as proxy:
                            reader, writer = await real_connect(*proxy.sockets[0].getsockname())
                            try:
                                writer.write(request)
                                await writer.drain()
                                self.assertEqual(await asyncio.wait_for(reader.readexactly(len(response)), 5), response)
                                if upstream_closes:
                                    self.assertEqual(await asyncio.wait_for(reader.read(), 5), b'')
                                else:
                                    writer.close()
                                    await writer.wait_closed()
                                # Fixture watchdogs: closed peers must not leave live bridge tasks.
                                await asyncio.wait_for(upstream_done.wait(), 5)
                                await asyncio.wait_for(bridge_done.wait(), 5)
                            finally:
                                writer.close()
                                await writer.wait_closed()
                self.assertEqual(received, [request] if upstream_closes else [request, b''])
                self.assertEqual(errors, [])

    async def test_upstream_connection_failure_closes_client_and_remains_visible(self):
        real_connect = asyncio.open_connection
        errors = []
        finished = asyncio.Event()

        async def bridge(reader, writer):
            try:
                await fixture.bridge(reader, writer)
            except Exception as error:
                errors.append(error)
            finally:
                finished.set()

        with patch.object(fixture.asyncio, 'open_connection', side_effect=ConnectionRefusedError('fixture refusal')):
            async with await asyncio.start_server(bridge, '127.0.0.1', 0) as proxy:
                reader, writer = await real_connect(*proxy.sockets[0].getsockname())
                try:
                    self.assertEqual(await asyncio.wait_for(reader.read(), 5), b'')
                    await asyncio.wait_for(finished.wait(), 5)
                finally:
                    writer.close()
                    await writer.wait_closed()
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ConnectionRefusedError)
