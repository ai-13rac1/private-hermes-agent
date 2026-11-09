"""Public-only raster retrieval over the namespace's existing transparent Tor route.

Connect to a checked numeric IPv4 address, preserving the original HTTP Host/TLS
SNI. No hostname is resolved again between validation and connection. This is
necessary because the agent also has explicitly privileged internal routes.
"""
import http.client
import io
import ipaddress
import re
import socket
import ssl
from urllib.parse import urljoin, urlsplit
import warnings

MAX_BYTES = 25 * 1024 * 1024  # Native Hermes image endpoint limit.
SOCKET_TIMEOUT = 60  # Per socket operation; allow for Tor latency.
MAX_REDIRECTS = 5
RASTER_TYPES = {'PNG': 'image/png', 'JPEG': 'image/jpeg', 'GIF': 'image/gif',
                'WEBP': 'image/webp', 'BMP': 'image/bmp', 'ICO': 'image/x-icon'}


class ImageRefused(Exception):
    def __init__(self, status, reason):
        self.status, self.reason = status, reason
        super().__init__(reason)


def parse_url(url):
    if not isinstance(url, str) or not url or any(ord(c) <= 32 or ord(c) >= 127 or c == '\\' for c in url):
        raise ImageRefused(400, 'Use an encoded public HTTP(S) image URL')
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port
        if port is None:
            port = 443 if parsed.scheme == 'https' else 80
        if (parsed.scheme not in ('http', 'https') or not host or parsed.username is not None
                or parsed.password is not None or parsed.fragment or parsed.netloc.endswith(':')
                or not 1 <= port <= 65535):
            raise ValueError()
        # DNS names use a conventional ASCII spelling. Reject alternate numeric
        # forms instead of letting libc interpret them differently from the URL.
        host = host.lower().rstrip('.')
        if host.split('.')[-1].isdigit() or host.startswith('0x'):
            address = ipaddress.IPv4Address(host)
            if str(address) != host or not address.is_global:
                raise ValueError()
        elif (len(host) > 253 or '.' not in host or host.endswith(('.local', '.localhost', '.onion'))
              or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
                     for label in host.split('.'))):
            raise ValueError()
    except ValueError:
        raise ImageRefused(400, 'Use a public HTTP(S) image destination') from None
    default = 443 if parsed.scheme == 'https' else 80
    authority = host if port == default else f'{host}:{port}'
    origin = f'{parsed.scheme}://{authority}'
    target = parsed.path or '/'
    if parsed.query:
        target += '?' + parsed.query
    return parsed.scheme, host, port, authority, origin, target


def public_addresses(host, port):
    try:
        answers = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        addresses = list(dict.fromkeys(answer[4][0] for answer in answers))
        if not addresses or any(not ipaddress.IPv4Address(ip).is_global for ip in addresses):
            raise ImageRefused(403, 'Image destination is not public IPv4')
        return addresses
    except (OSError, ValueError):
        raise ImageRefused(502, 'Public image DNS resolution failed') from None


def open_response(parts):
    scheme, host, port, authority, _origin, target = parts
    addresses = public_addresses(host, port)
    # No automatic reconnect, proxy, cookie jar or HTTP authentication machinery.
    # A failed attempt may try another already checked address, never re-resolve.
    last_error = None
    for address in addresses:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(SOCKET_TIMEOUT)
        connection = http.client.HTTPConnection(host, port, timeout=SOCKET_TIMEOUT)
        try:
            sock.connect((address, port))
            if scheme == 'https':
                sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
            connection.sock = sock
            connection.putrequest('GET', target, skip_host=True, skip_accept_encoding=True)
            connection.putheader('Host', authority)
            connection.putheader('Accept', ', '.join(RASTER_TYPES.values()))
            connection.putheader('Connection', 'close')
            connection.endheaders()
            return connection, connection.getresponse()
        except (OSError, http.client.HTTPException) as error:
            sock.close()
            connection.close()
            last_error = error
    raise ImageRefused(502, 'Image connection failed; retry through Tor or open externally') from last_error


def raster_type(data, advertised):
    from PIL import Image, UnidentifiedImageError
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                mime = RASTER_TYPES.get(image.format)
                if not mime or advertised != mime:
                    raise ImageRefused(415, 'Only validated passive raster images are supported')
                image.verify()
        return mime
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError,
            Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ImageRefused(415, 'The response is not a supported passive raster image') from None


def fetch_image(url, *, same_origin_only=False):
    initial_origin = parse_url(url)[4]
    for hop in range(MAX_REDIRECTS + 1):
        parts = parse_url(url)
        # Consent is checked BEFORE next-hop resolution, including load once.
        if same_origin_only and parts[4] != initial_origin:
            raise ImageRefused(403, 'Cross-origin image redirects require opening externally')
        connection, response = open_response(parts)
        try:
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader('Location')
                if not location or hop == MAX_REDIRECTS:
                    raise ImageRefused(502, 'Image redirect limit or missing destination')
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise ImageRefused(502, 'Image server did not return a complete image')
            if response.getheader('Content-Encoding', 'identity').lower() != 'identity':
                raise ImageRefused(415, 'Compressed HTTP image responses are unsupported')
            length = response.getheader('Content-Length')
            if length is not None:
                try:
                    length = int(length)
                except ValueError:
                    raise ImageRefused(502, 'Invalid image response length') from None
                if length < 0 or length > MAX_BYTES:
                    raise ImageRefused(413, 'Image exceeds the native 25 MiB limit')
            data = bytearray()
            while True:
                chunk = response.read(min(65536, MAX_BYTES + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
                if len(data) > MAX_BYTES:
                    raise ImageRefused(413, 'Image exceeds the native 25 MiB limit')
            advertised = response.getheader('Content-Type', '').split(';', 1)[0].strip().lower()
            mime = raster_type(data, advertised)
            return bytes(data), mime
        except (OSError, http.client.HTTPException):
            raise ImageRefused(502, 'Image transfer failed; retry through Tor or open externally') from None
        finally:
            response.close()
            connection.close()
    raise ImageRefused(502, 'Image redirect limit reached')
