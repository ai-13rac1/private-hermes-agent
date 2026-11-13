"""Browser qualification CONNECT observer; forwards only to local fixtures."""
from http.server import BaseHTTPRequestHandler
import select
import socket
import ssl

tunnels = []


class Observer(BaseHTTPRequestHandler):
    # CONNECT switches to raw socket reads. A buffered HTTP parser can consume
    # early tunnel bytes along with the headers and strand them outside select().
    rbufsize = 0

    def log_message(self, *args):
        pass

    def do_CONNECT(self):
        host, port = self.path.rsplit(':', 1)
        tunnels.append((host, int(port)))
        target = (int(port) if host == 'webapp-test.example.ts.net' and int(port) == 10000 else
                  19202 if host in ('public.test', 'www.youtube.com', 'www.youtube-nocookie.com') else None)
        if target is None:
            self.send_error(502, 'Uncontrolled destination denied by fixture')
            return
        upstream = socket.create_connection(('127.0.0.1', target))
        self.send_response(200)
        self.end_headers()
        sockets = [self.connection, upstream]
        try:
            while True:
                readable, _, _ = select.select(sockets, [], [])
                for source in readable:
                    data = source.recv(65536)
                    if not data:
                        return
                    (upstream if source is self.connection else self.connection).sendall(data)
        except (OSError, ssl.SSLError):
            pass
        finally:
            upstream.close()
