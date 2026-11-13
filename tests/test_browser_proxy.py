"""CONNECT bytes must survive HTTP parsing without opening uncontrolled targets."""
from http.server import ThreadingHTTPServer
import socket
import socketserver
import threading
import unittest
from unittest.mock import patch

import browser_proxy


class Echo(socketserver.BaseRequestHandler):
    def handle(self):
        while data := self.request.recv(65536):
            self.request.sendall(data)


class EchoServer(socketserver.ThreadingTCPServer):
    daemon_threads = True


class BrowserProxyTests(unittest.TestCase):
    def test_connect_and_early_tunnel_bytes_in_same_write(self):
        real_connect = socket.create_connection
        with EchoServer(('127.0.0.1', 0), Echo) as upstream, \
                ThreadingHTTPServer(('127.0.0.1', 0), browser_proxy.Observer) as proxy:
            threading.Thread(target=upstream.serve_forever, daemon=True).start()
            threading.Thread(target=proxy.serve_forever, daemon=True).start()
            try:
                with patch.object(browser_proxy.socket, 'create_connection',
                                  side_effect=lambda *_: real_connect(upstream.server_address)) as connect:
                    with real_connect(proxy.server_address) as client:
                        client.settimeout(5)  # Loopback fixture watchdog, not a stream deadline.
                        payload = b'\x16\x03\x01controlled early tunnel bytes'
                        client.sendall(b'CONNECT webapp-test.example.ts.net:10000 HTTP/1.1\r\n'
                                       b'Host: webapp-test.example.ts.net\r\n\r\n' + payload)
                        headers = b''
                        while not headers.endswith(b'\r\n\r\n'):
                            byte = client.recv(1)
                            self.assertTrue(byte, 'Proxy closed before its CONNECT response')
                            headers += byte
                        self.assertIn(b' 200 ', headers.split(b'\r\n', 1)[0])
                        received = b''
                        while len(received) < len(payload):
                            chunk = client.recv(len(payload) - len(received))
                            self.assertTrue(chunk, 'Tunnel closed before all bytes arrived')
                            received += chunk
                        self.assertEqual(received, payload)
                    connect.assert_called_once_with(('127.0.0.1', 10000))
            finally:
                proxy.shutdown()
                upstream.shutdown()

    def test_uncontrolled_connect_target_is_denied_without_a_connection(self):
        real_connect = socket.create_connection
        with ThreadingHTTPServer(('127.0.0.1', 0), browser_proxy.Observer) as proxy:
            threading.Thread(target=proxy.serve_forever, daemon=True).start()
            try:
                with patch.object(browser_proxy.socket, 'create_connection') as connect:
                    with real_connect(proxy.server_address) as client:
                        client.settimeout(5)
                        client.sendall(b'CONNECT uncontrolled.invalid:443 HTTP/1.1\r\n'
                                       b'Host: uncontrolled.invalid\r\n\r\n')
                        with client.makefile('rb') as response:
                            self.assertIn(b' 502 ', response.readline())
                    connect.assert_not_called()
            finally:
                proxy.shutdown()
